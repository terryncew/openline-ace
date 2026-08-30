import re

def slugify(text):
    return text.lower().replace(" ", "-")

def bounded_sum(values):
    return sum(values) & 0xffffffff

def median(values):
    xs = sorted(values)
    return xs[len(xs)//2]
