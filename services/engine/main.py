import time, sys

print("Bitcor engine started", flush=True)
try:
    while True:
        time.sleep(10)
except KeyboardInterrupt:
    sys.exit(0)
