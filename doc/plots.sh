
# SDSS section
python examples/designdoc.py --root out --drillxy 1665,1543 --order 1,0,2 --pat "design-sdss-%(name)s.pdf"

# Monotonic section
python examples/designdoc.py --root out --drillxy 1545,2131 --pat "design-mono1-%(name)s.pdf" --figh 2.5
python examples/designdoc.py --root out --drillxy 1545,2131 --pat "design-mono2-%(name)s.pdf" --figh 2.5 --mono

python examples/designdoc.py --root out --drillxy 1378,3971 --pat "design-mono3-%(name)s.pdf" --figw 3
python examples/designdoc.py --root out --drillxy 1378,3971 --pat "design-mono4-%(name)s.pdf" --figw 3 --mono

# Median-filter section
python examples/designdoc.py --root out --drillxy 1545,2131 --pat "design-med1-%(name)s.pdf" --figh 2.5 --median
python examples/designdoc.py --root out --drillxy 1378,3971 --pat "design-med2-%(name)s.pdf" --figw 3   --median

