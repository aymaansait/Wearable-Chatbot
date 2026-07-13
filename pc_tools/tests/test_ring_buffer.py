import numpy as np
from ring_buffer import RingBuffer

# Create a ring buffer capable of storing 10 samples
rb = RingBuffer(10)

print("Empty Buffer:")
print(rb.get())

print("\nAppending [1,2,3]")
rb.append(np.array([1, 2, 3], dtype=np.int32))
print(rb.get())

print("\nAppending [4,5,6,7]")
rb.append(np.array([4, 5, 6, 7], dtype=np.int32))
print(rb.get())

print("\nAppending [8,9,10,11,12]")
rb.append(np.array([8, 9, 10, 11, 12], dtype=np.int32))
print(rb.get())

print("\nAppending [13,14,15]")
rb.append(np.array([13, 14, 15], dtype=np.int32))
print(rb.get())