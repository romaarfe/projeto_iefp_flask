# forsearch.py

# USADO PARA BUSCAR CARTAZES EM OUTRA API (OMDB)
# COMPLEMENTA AS INFORMAÇÕES DO IMDB

import requests
import json

def searchreq(searchquery):
    params ={
 	   "apikey":'4c2d5800',
    	"s":searchquery
    }
    url = "https://www.omdbapi.com/"
    data = requests.get(url,params=params)
    print(data)


    content = data.json()
    return content