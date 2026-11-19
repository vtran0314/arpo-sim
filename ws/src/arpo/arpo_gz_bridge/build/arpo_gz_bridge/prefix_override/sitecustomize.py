import sys
if sys.prefix == '/usr':
    sys.real_prefix = sys.prefix
    sys.prefix = sys.exec_prefix = '/home/dev/ws/src/arpo_gz_bridge/install/arpo_gz_bridge'
