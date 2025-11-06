import threading
import queue
import time
import requests
from datetime import datetime
from logger import logger
from factory.monitor_factory import MonitorFactory
from factory.response_parser_factory import ResponseParserFactory

class StatusMonitor:
    def __init__(self, apps, num_workers = 3):
        """
        Initialize the status monitoring system.

        Args:
            apps: List of dicts with 'name' and 'url' keys
            num_workers: Number of child worker threads
        """
        self.apps = apps
        self.num_workers = num_workers

        self.downtime_queue = queue.Queue()
        self.recovery_queue = queue.Queue()
        self.monitoring_apps = set()
        self.monitoring_lock = threading.Lock()

        # Exponential backoff tracking for each app
        self.app_backoff = {}  # {app_name: next_check_time}
        self.app_interval = {}  # {app_name: current_interval}
        self.backoff_lock = threading.Lock()

        # Backoff configuration (1 min to 10 min)
        self.min_interval = 60  # 1 min
        self.max_interval = 600  # 10 minutes

        self.running = True
        self.main_worker_thread = None
        self.child_worker_threads = []

    def reset_backoff(self, app_name):
        """Reset backoff interval for an app to minimum."""
        with self.backoff_lock:
            self.app_interval[app_name] = self.min_interval
            self.app_backoff[app_name] = time.time()

    def increase_backoff(self, app_name):
        """Increase backoff interval exponentially (double it, up to max)."""
        with self.backoff_lock:
            current_interval = self.app_interval.get(app_name, self.min_interval)
            new_interval = min(current_interval * 2, self.max_interval)
            self.app_interval[app_name] = new_interval
            self.app_backoff[app_name] = time.time() + new_interval
            logger.debug(f"Increased backoff for {app_name} to {new_interval}s")

    def should_check_app(self, app_name):
        """Check if enough time has passed to check this app again."""
        with self.backoff_lock:
            if app_name not in self.app_backoff:
                self.app_backoff[app_name] = time.time()
                self.app_interval[app_name] = self.min_interval
                return True

            next_check = self.app_backoff.get(app_name, 0)
            return time.time() >= next_check

    def check_status(self, app):
        """
        Check if an app's status endpoint is up.

        Args:
            app: Dict with 'name' and 'url' keys

        Returns:
            True if app is up, False otherwise
        """
        try:
            data = MonitorFactory.fetch_transactions(source=app['name'], base_url=app['url'])
            if data:
                data = ResponseParserFactory.parse_response(source=app['name'], data=data)
                return data
            return {}
        except requests.exceptions.RequestException as e:
            logger.debug(f"Error checking {app['name']}: {e}")
            return False

    def main_worker(self):
        """
        Main worker thread that periodically checks all apps.
        Uses exponential backoff (1s to 10min) when apps are healthy.
        If an app is down, queues it for child workers to monitor.
        Also processes recovery notifications from child workers.
        """
        logger.info("Main worker started")

        while self.running:
            # Check for recovered apps from child workers
            while not self.recovery_queue.empty():
                try:
                    recovered_app = self.recovery_queue.get_nowait()
                    with self.monitoring_lock:
                        self.monitoring_apps.discard(recovered_app['name'])

                    # Reset backoff when app recovers
                    self.reset_backoff(recovered_app['name'])
                    # logger.info(f"{recovered_app['name']} recovered and back to main monitoring")
                    self.recovery_queue.task_done()
                except queue.Empty:
                    break

            # Check status of apps that are due for checking
            for app in self.apps:
                # Skip if already being monitored by a child worker
                with self.monitoring_lock:
                    if app['name'] in self.monitoring_apps:
                        continue

                # Check if enough time has passed (exponential backoff)
                # if not self.should_check_app(app['name']):
                #     continue

                data = self.check_status(app)
                # import pdb
                # pdb.set_trace()

                if data and data['status'] != 'resolved':
                    logger.info(f"[{datetime.now()}] product: {data['name']}")
                    logger.info(f"status: {data['status']}")
                    with self.monitoring_lock:
                        if app['name'] not in self.monitoring_apps:
                            self.monitoring_apps.add(app['name'])
                            self.downtime_queue.put(app)
                else:
                    self.increase_backoff(app['name'])

            # Sleep briefly to avoid busy waiting
            time.sleep(0.5)

        logger.info("Main worker stopped")

    def child_worker(self, worker_id: int):
        """
        Child worker thread that monitors apps with downtime.
        Continuously checks status and logs until app is up again.

        Args:
            worker_id: Unique identifier for this worker
        """
        logger.info(f"Child worker {worker_id} started")

        while self.running:
            try:
                # Get an app to monitor (blocks with timeout)
                app = self.downtime_queue.get(timeout=2)

                logger.info(f"Child worker {worker_id} monitoring {app['name']}")

                # Keep checking until app is back up
                while self.running:
                    data = self.check_status(app)

                    if data:
                        logger.info(f"[{datetime.now()}] product: {data['name']}")
                        logger.info(f"status: {data['status']}")
                        self.increase_backoff(app['name'])
                        with self.monitoring_lock:
                            if app['name'] not in self.monitoring_apps:
                                self.monitoring_apps.add(app['name'])
                                self.downtime_queue.put(app)
                    else:
                        self.recovery_queue.put(app)
                        break

                    time.sleep(5)
                self.downtime_queue.task_done()

            except queue.Empty:
                continue
            except Exception as e:
                logger.error(f"Child worker {worker_id} error: {e}")

        logger.info(f"Child worker {worker_id} stopped")

    def start(self):
        """Start all worker threads."""
        # Start main worker
        self.main_worker_thread = threading.Thread(
            target=self.main_worker,
            name="main_worker"
        )
        self.main_worker_thread.start()

        # Start child workers
        for i in range(self.num_workers):
            worker_thread = threading.Thread(
                target=self.child_worker,
                args=(i + 1,),
                name=f"child_worker_{i + 1}"
            )
            worker_thread.start()
            self.child_worker_threads.append(worker_thread)

        logger.info(f"Started monitoring system with {self.num_workers} child workers")

    def stop(self):
        """Stop all worker threads gracefully."""
        logger.info("Stopping monitoring system...")
        self.running = False

        # Wait for all threads to finish
        if self.main_worker_thread:
            self.main_worker_thread.join()

        for worker_thread in self.child_worker_threads:
            worker_thread.join()

        logger.info("Monitoring system stopped")
