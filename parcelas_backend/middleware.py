import time

class TimingMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        t0 = time.time()
        response = self.get_response(request)
        duration = (time.time() - t0) * 1000
        print(f"[TIMING] {request.method} {request.path} -> {duration:.0f}ms")
        return response
