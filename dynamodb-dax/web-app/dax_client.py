"""
Hai Tran: 12 JUN 2022 
DynamoDB with DAX Performance 
"""

from asyncore import write
import os
import uuid
from concurrent.futures import ThreadPoolExecutor
import names 
import amazondax 
import boto3
import random 
import datetime
from boto3.dynamodb.conditions import Key
import time
import matplotlib.pyplot as plt

# configure region 
REGION = os.environ.get("AWS_DEFAULT_REGION", "ap-southeast-1")
# dax endpoint 
DAX_ENDPOINT = "dax://daxclusterdemo.a7wlr3.dax-clusters.ap-southeast-1.amazonaws.com"
# table name 
TABLE_NAME = "GamePlayer"
# game title 
GAME_TITLES = [
    'Galaxy Invaders',
    'Meteor Blasters',
]
# number of thread 
NUM_THREAD = 100
# number of user 
NUM_USER = 1000
# get a single user 
USER_ID_SINGLE = '8577287c-eb20-11ec-a8e5-022d3357acbe'

def create_table(table_name: str) -> None:
    """
    create a table
    """
    # db client, optional region specified here
    db_client = boto3.client('dynamodb')
    # create a table
    res = db_client.create_table(
        TableName=table_name,
        AttributeDefinitions=[
            {
                'AttributeName': 'UserId',
                'AttributeType': 'S'
            }
        ],
        # KeySchema and Attribute should be the same
        KeySchema=[
            {
                'AttributeName': 'UserId',
                'KeyType': 'HASH'
            }
        ],
        # PAY_PER_REQUEST when load is unpredictable
        # PROVISIONED when load is predictable
        BillingMode="PAY_PER_REQUEST"
    )
    # print table meta data 
    print(res)



def get_table(table_name: str, mode='ddb'):
  """
  get table 
  """
  if mode=='dax':
    # dax client 
    dax = amazondax.AmazonDaxClient.resource(endpoint_url=DAX_ENDPOINT)
    # table  
    table = dax.Table(table_name)
  else: 
    # create ddb client
    ddb = boto3.resource('dynamodb')
    # table
    table = ddb.Table(table_name)
  # return 
  return table 
    

def scan_user_ids(table_name: str, no_user: int, mode='ddb'):
  """
  always return first no_user items 
  """
  # table 
  table = get_table(table_name, mode)
  # scan 
  res = table.scan(
    Limit=no_user
  )
  # print(res['Items'])
  # return user ids 
  user_ids = [item['UserId'] for item in res['Items']]
  return user_ids



def write_table(table_name: str, mode='dax') -> None:
  """
  write data items to a table 
  """
  # table
  table = get_table(table_name, mode)
  # create a new item
  for game_title in GAME_TITLES:
      for k in range(NUM_USER):
          res = table.put_item(
              Item={
                  'UserId': str(uuid.uuid1()),
                  "UserName": names.get_full_name(),
                  'GameTitle': game_title,
                  'Score': random.randint(1000, 6000),
                  'Wins': random.randint(0, 100),
                  'Losses': random.randint(5, 50),
                  'CreatedTime': int(datetime.datetime.now().timestamp() * 1000)
              }
          )
          print(k)


def write_table_thread(table_name: str, mode='dax') -> None: 
  """
  """
  with ThreadPoolExecutor(max_workers=NUM_THREAD) as executor:
    for k in range(1, NUM_THREAD):
      executor.submit(write_table, TABLE_NAME)


def get_items_by_primary_key(table_name: str, mode='dax', no_user=100):
  """
  """
  # buffer items 
  items, latencies = [], []
  # buffer time lags 
  latencies = []
  # table 
  table = get_table(table_name, mode)
  # get user id 
  user_ids = scan_user_ids(table_name, no_user, mode=mode)
  # loop get item 
  for user_id in user_ids:
    start = time.perf_counter()
    res = table.get_item(
      Key={"UserId": user_id}
    )
    end = time.perf_counter()
    # time lag in ms 
    duration = (end - start) * 1000
    print(f'{mode} get-item {res["Item"]["UserId"]} latency: {duration:.4f}ms ')
    # print(res)
    # tag latency to each query 
    item = res['Item']
    item['latency'] = duration
    # parse items 
    items.append(item)
    # buffer time lag 
    latencies.append(duration)
  # return 
  return {"latencies": latencies[2:], "items": items[2:]}


def query_items(table_name: str, mode='dax', no_user=100): 
  """
  """
  # buffer time lags
  latencies = []
  # buffer items 
  items = []
  # table
  table = get_table(table_name, mode)
  # get some user ids 
  user_ids = scan_user_ids(table_name, no_user, mode)
  # loop over user_ids
  for user_id in user_ids:
    # query by user_id 
    start = time.perf_counter()
    res = table.query(
      KeyConditionExpression=Key('UserId').eq(user_id),
      ScanIndexForward=False)
    end = time.perf_counter()
    # time lag 
    duration = (end - start) * 1000
    print(f'{mode} query latency {duration:.4f} ms')
    # tag latency to each query 
    for item in res['Items']:
      item['latency'] = duration
    # parse items 
    items += res['Items']
    # buffer time lag 
    latencies.append(duration)
  # return 
  return {"latencies": latencies[2:], "items": items[2:]}


def delete_table(table_name) -> None:
  """
  delete a table 
  """ 
  # get table 
  table = get_table(table_name)
  # delete table 
  res = table.delete()
  # print 
  print(res)

if __name__=="__main__":
  # create_table(TABLE_NAME)
  # write_table(TABLE_NAME, mode='ddb')
  # write_table_thread(TABLE_NAME)
  # scan_user_ids(TABLE_NAME, no_user=10, mode='ddb')
  # get_item_by_id(table_name,"120")
  # get_items_wo_dax(table_name, 1)
  # get_items_wi_dax(table_name, 1)
  # delete_table(TABLE_NAME)
  dic_wo_dax = get_items_by_primary_key(TABLE_NAME, mode='ddb', no_user=100)
  dic_wi_dax = get_items_by_primary_key(TABLE_NAME, mode='dax', no_user=100)
  fig,axes = plt.subplots(1,1,figsize=(10,5))
  axes.plot(dic_wo_dax['latencies'][1:],'k--o',markersize=3,linewidth=0.5)
  axes.plot(dic_wi_dax['latencies'][1:],'b--o',markersize=3,linewidth=0.5)
  axes.legend(['wo-dax','wi-dax'])
  axes.set_ylabel('milisecond')
  axes.set_xlabel('read db')
  axes.set_yticks([k for k in range(10)])
  axes.set_ylim(0,10)
  fig.suptitle('DAX performance')
  fig.savefig('dax_performance.png')