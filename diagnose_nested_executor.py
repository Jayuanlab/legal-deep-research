"""Reproduce the auxiliary launcher's interpreter-shutdown failure, no model call."""
import time
from concurrent.futures import ThreadPoolExecutor
def worker():
 time.sleep(.2)
 try:
  with ThreadPoolExecutor() as nested:nested.submit(int).result()
 except RuntimeError as error:print(type(error).__name__+': '+str(error),flush=True)
pool=ThreadPoolExecutor();pool.submit(worker)
