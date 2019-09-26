from os import environ as env
import multiprocessing
import urllib

PORT = int(env.get("PORT", 4004))
DEBUG_MODE = int(env.get("DEBUG_MODE", 0))
ZOOKEEPER_HOST = "192.168.200.198:4184,192.168.200.197:4184"
MONGODB_HOST = "mongodb+srv://cubus:"+ urllib.quote_plus("@Cu2010bus") +"@cluster0-kxvpc.mongodb.net/test?retryWrites=true&w=majority"
REDIS_HOST = "redis-11737.c1.asia-northeast1-1.gce.cloud.redislabs.com"
REDIS_PORT = "11737"
REDIS_PASSWORD = "vPt0IxefzMh8SdhfgbwzI5ltabzkz8BK"
