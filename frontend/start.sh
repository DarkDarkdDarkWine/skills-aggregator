#!/bin/sh
rm -f /usr/share/nginx/html/docker-entrypoint.sh /usr/share/nginx/html/npm /usr/share/nginx/html/*.sh 2>/dev/null
exec nginx -g 'daemon off;'
