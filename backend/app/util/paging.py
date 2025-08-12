# app/util/paging.py
def clamp_page(page: int) -> int: return max(1, int(page))
def clamp_page_size(n: int, lo: int = 1, hi: int = 100) -> int: return max(lo, min(hi, int(n)))
def offset_for(page: int, page_size: int) -> int: return (page - 1) * page_size
