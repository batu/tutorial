from bs4 import BeautifulSoup
import urllib2

#url = "http://www.practicallynetworked.com/security/set-up-a-personal-windows-vpn.htm"
url = "http://www.cprogramming.com/begin.html"
#url = "https://developer.atlassian.com/display/DOCS/Set+Up+the+Eclipse+IDE+for+Windows"
#url = "http://www.pcworld.com/article/210562/how_set_up_vpn_in_windows_7.html"
#url = "http://www.pythonforbeginners.com"
#url = "http://code.tutsplus.com/tutorials/pure-what-why-how--net-33320"

content = urllib2.urlopen(url).read()

soup = BeautifulSoup(content)

soup.encode(encoding="utf-8")
body = soup.get_text()

print soup.prettify(encoding='utf-8')







