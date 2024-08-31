import grequests
import time

all_user_stories="""query{
  allUserStories{
  edges{
    node{
      id
      pk
      likes{
        edges{
          node{
            id
            objectId
          }
        }
      }
      comments{
      edges{
          node{
            commentDescription
            id
          }
        }		
      }
    }
  }		
  }
}"""

user_query = """query{
  users{
    username
  }
}"""

moments_query="""query{allMoments{
    user{
      username
    }
  }
}"""

header = {'Authorization' : "Token admin_token"}
def checkLoad():
    
    url = 'https://api.chatadmin-mod.click/'
    start=time.time()
    rs=[]
    for i in range(300):
        rs.append(grequests.get(url,headers=header,json={'query':user_query}))
    for i in range(300):
        rs.append(grequests.get(url,headers=header,json={'query':moments_query}))
    for i in range(300):
        rs.append(grequests.get(url,headers=header,json={'query':all_user_stories}))

    print("Request time: ",time.time()-start,"secs")
    resps=grequests.map(rs)
    print("Response complete time: ",time.time()-start,"secs")
    
    for i in range(len(resps)):
        if not resps[i]:
            print(i, resps[i])
            continue
        if resps[i].status_code!=200:
            print(f"request {i+1} failed with status code {resps[i].status_code}\nresponse_data: {resps[i].text}")

    return resps

checkLoad()