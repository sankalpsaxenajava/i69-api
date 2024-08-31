FROM redis:6.2.6-alpine3.15
COPY ./docker/.conf.d/redis/users.acl /usr/local/etc/redis/users.acl
COPY ./docker/.conf.d/redis/redis.conf /usr/local/etc/redis/redis.conf
CMD [ "redis-server", "/usr/local/etc/redis/redis.conf" ]
