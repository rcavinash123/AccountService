from flask import Flask
from flask import jsonify
from flask import request
from flask_pymongo import PyMongo
from pymongo import MongoClient
import urllib
import redis
import json
from bson.objectid import ObjectId
import psutil
from kazoo.client import KazooClient
import config
import logging
from flask import Response
from bson import json_util

#FORMAT = '%(asctime)-15s %(clientip)s %(user)-8s %(message)s'
logging.basicConfig(level=logging.DEBUG)

app = Flask(__name__)
mongodb_ok = False
redis_ok = False

mongourl = ""
mongousername = ""
mongopassword = ""
redishost=""
redisport=""
redispwd=""

# App route to get the account balance -------------------------------------------------------------------
# Input Params : ID
@app.route('/acct/balanceget/<ID>',methods=['GET'])
def balanceget(ID):
    logging.debug("Requested for account balance recieved")
    try:
        client = MongoClient(mongourl,username=mongousername,password=mongopassword)
        mongodb = client.CubusDBTest

        redisdb = redis.Redis(host=redishost,port=redisport,password=redispwd)
        redisdb.ping()

        logging.debug("Before getting users from mongo db")

        users = mongodb.users
        result = []
        redisData = None
        redisData = redisdb.get(str(ID))
        print("RedisData : " + str(redisData))
        if redisData!=None:
            logging.debug("redis data : " + redisData)
            jsonData = json.loads(redisData)
            userId = jsonData["result"]["userId"]
            logging.debug("userId : " + str(userId))
            user = users.find_one({'userId' : userId})

            if user: 
                aggr = [
                    {
                    '$lookup': {
                        'from': 'userToAcctMapping', 
                        'localField': 'userId', 
                        'foreignField': 'userId', 
                        'as': 'UserAccounts'
                        }
                    }, 
                    {
                    '$lookup': {
                        'from': 'acctInfo', 
                        'localField': 'UserAccounts.userId', 
                        'foreignField': 'userId', 
                        'as': 'UserAccounts.AccountInfo'
                        }
                    },
                    { 
                    '$match' : { 
                        'userId' : userId,
                        } 
                    },
                    { 
                    "$project" : { 
                        "_id": 0,
                        "regDate":0,
                        "UserAccounts":{
                            "_id":0,
                        },
                        "UserAccounts.AccountInfo":{
                            "_id":0,
                        },
                    }
                    }
                ]
                acctData = list(users.aggregate(aggr))
                logging.debug("After getting data from mongo db")
                strData = acctData[0]
                client.close()
                result = json.dumps({"result":{"status":"true","code":"200","data":strData} })
                return Response(result,status=200,content_type="application/json")
            else:
                result = json.dumps({ "result":{ "status":"false","code":"500","reason":"User not found" } })
                client.close()
                return result
        else:
            result = json.dumps({ "result":{ "status":"false","code":"500","reason":"User not found" } })
            client.close()
            return result    
    except Exception as ex:
        result = json.dumps({ "result":{ "status":"false","code":"500","reason":str(ex) } })
        return result

@app.route('/acct/healthz',methods=['GET'])
def getUsageParams():
    MongoOK = False
    RedisOK = False
    try:
        zk = KazooClient(hosts=config.ZOOKEEPER_HOST,timeout=5,max_retries=3)
        zk.start()
        logging.debug("ZOO Ok")
        zk.stop()

        client = MongoClient(mongourl,username=mongousername,password=mongopassword)
        mongodb = client.CubusDBTest
        logging.debug("MongoDB Ok")
        MongoOK = True
        client.close()

        redisdb = redis.Redis(host=redishost,port=redisport,password=redispwd)
        logging.debug("MongoDB Ok")
        RedisOK = True

        jresp = json.dumps({"result":{"status":"true","code":"200","reason":"None"}})
        resp = Response(jresp, status=200, mimetype='application/json')
        return resp

    except Exception as ex:
        Reason=None
        if MongoOK == False:
            logging.debug("Failed to connect to MongoDB")
            Reason = "Failed to connect to MongoDB"
        elif RedisOK == False:
            logging.debug("Failed to connect to RedisDB")
            Reason = "Failed to connect to RedisDB"
        else:
            logging.debug("Failed to connect to zoo keeper")
            Reason = "Failed to connect to zoo keeper"

        jresp = json.dumps({"result":{"status":"fail","code":"500","reason":Reason + " Exception : " + str(ex)}})
        resp = Response(jresp, status=500, mimetype='application/json')
        return resp

if __name__ == '__main__':
    try:
        zk = KazooClient(hosts=config.ZOOKEEPER_HOST,timeout=5,max_retries=3)
        zk.start()
        try:
            if zk.exists("/databases/mongodb"):
                mongodata = zk.get("/databases/mongodb")
                mongodata = json.loads(mongodata[0])
                mongourl = mongodata["endpoints"]["url"]
                mongousername = mongodata["endpoints"]["username"]
                mongopassword = mongodata["endpoints"]["password"]
                logging.debug("Fetched mongodb config from zookeeper")
            else:
                mongourl = config.MONGODB_HOST
                mongousername = config.MONGODB_USERNAME
                mongopassword = config.MONGODB_PWD
        except:
            logging.debug("Failed to fetch mongodb config from zookeeper. Reverting to default value")
            mongourl = config.MONGODB_HOST
            mongousername = config.MONGODB_USERNAME
            mongopassword = config.MONGODB_PWD
    
        try:
            if zk.exists("/databases/redisdb"):
                redisdata = zk.get("/databases/redisdb")
                redisdata = json.loads(redisdata[0])
                redishost = redisdata["endpoints"]["host"]
                redisport = redisdata["endpoints"]["port"]
                redispwd = redisdata["endpoints"]["password"]
                logging.debug("Fetched redisdb config from zookeeper")
            else:
                redishost = config.REDIS_HOST
                redisport = config.REDIS_PORT
                redispwd = config.REDIS_PASSWORD
        except:
            logging.debug("Failed to fetch redis config from zookeeper. Reverting to default value")
            redishost = config.REDIS_HOST
            redisport = config.REDIS_PORT
            redispwd = config.REDIS_PASSWORD
        
        data = json.dumps({
                "balanceget":{
                    "url":"http://accountservice.default.svc.cluster.local:4004/acct/balanceget/"
                },
                "healthcheck":{
                    "url":"http://accountservice.default.svc.cluster.local:4004/acct/healthz"
                }
            })

        if zk.exists("/microservices/accountservice"):
            logging.debug("Zookeeper Updating AccountService")
            zk.set("/microservices/accountservice",data)
            logging.debug("AccountService configuration updated")
        else:
            logging.debug("Zookeeper Creating AccountService")
            zk.create("/microservices/accountservice",data)
            logging.debug("AccountService configuration created")
            
        zk.stop()
        
    except:
        logging.debug("Failed to connect to zookeeper. Reverting to default value")
        redishost = config.REDIS_HOST
        redisport = config.REDIS_PORT
        redispwd = config.REDIS_PASSWORD
    
    app.run(debug=config.DEBUG_MODE,host='0.0.0.0',port=config.PORT)