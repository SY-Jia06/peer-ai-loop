import threading

class Singleton:
    """
    A thread-safe implementation of the Singleton pattern.
    """
    _instance = None
    _lock = threading.Lock()

    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            with cls._lock:
                # Double-checked locking to ensure thread safety
                if not cls._instance:
                    cls._instance = super(Singleton, cls).__new__(cls)
        return cls._instance

    def __init__(self, value=None):
        """
        Initialize the instance. 
        Note: In Python, __init__ is called every time the class is instantiated.
        We use a flag to prevent re-initialization.
        """
        if hasattr(self, '_initialized') and self._initialized:
            return
            
        self.value = value
        self._initialized = True

if __name__ == "__main__":
    # Test the Singleton
    s1 = Singleton("First Instance")
    s2 = Singleton("Second Instance")

    print(f"s1 value: {s1.value}")
    print(f"s2 value: {s2.value}")
    print(f"Are s1 and s2 the same object? {s1 is s2}")
