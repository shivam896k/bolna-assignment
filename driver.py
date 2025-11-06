import time
from logger import logger
from monitor import StatusMonitor

def main():
    apps = [
        {'name': 'openai', 'url': 'https://status.openai.com/proxy/status.openai.com/component_impacts'}
    ]

    monitor = StatusMonitor(apps, num_workers=3)
    monitor.start()

    try:
        logger.info("Monitoring started. Press Ctrl+C to stop.")
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        logger.info("Received interrupt signal")
    finally:
        monitor.stop()


if __name__ == "__main__":
    main()
