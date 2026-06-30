ssh root@192.168.105.41 "pvesh create /nodes/DOCKER41/qemu/100/spiceproxy --output-format json" \
  | python3 -c "
import json,sys
d=json.load(sys.stdin)
print('[virt-viewer]')
print('type=spice')
print('host='+d['host'])
print('tls-port='+str(d['tls-port']))
print('password='+d['password'])
print('proxy=http://192.168.105.41:3128')
print('host-subject='+d['host-subject'])
print('ca='+d['ca'])
print('delete-this-file=1')
" > /tmp/test.vv && remote-viewer /tmp/test.vv
