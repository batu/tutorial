#!/usr/bin/python

"""
Requires Python <= 2.5.X. Must rewrite bits of code for Python >= 2.6.X.

TODO:
- Amazon.com-like Statistically Improbable Phrases.
- Add parallelization, persistence of state.
"""

import HTMLParser, logging, operator, time, urllib, urllib2, urlparse
import BeautifulSoup, nltk


google_url        = 'http://www.google.com/search?hl=en&q=%s&num=%s'
yahoo_url         = 'http://search.yahooapis.com/WebSearchService/V1/webSearch?appid=yahoosearchwebrss&query=%s&results=%s&adult_ok=0&language=en'
headers           = { 'User-Agent' : 'Mozilla/5.0 (X11; U; Linux i686) Gecko/20071127 Firefox/2.0.0.11' }
search_lag_time   = 1
affinity_set      = set( [] )
W                 = set( [] )
T_visited         = set( [] )
T_to_be_visited   = []
ngram_histogram   = nltk.probability.FreqDist()
english_stopwords = set( nltk.corpus.stopwords.words( 'english' ) )

def powerset( l ):
  """
    A powerset generator. Can you think of a better way?
  """
  p = []
  if len( l ) == 0:
    yield p
  else:
    for b in xrange( 2 ** len( l ) ):
      del p[ : ]
      c = 0
      while b > 0:
        if b % 2 == 1:
          p.append( l[c] )
        b, c = b >> 1, c + 1
      yield p

def soup_to_ngrams( soup, ngram_limit ):
  """
    References:
      - http://www.python.org/dev/peps/pep-0265/
      - http://code.activestate.com/recipes/304440/
  """
  try:
    clean_html = nltk.util.clean_html( str( soup ) )
    # TODO: We want only words, hence the choice of token-izer; what about 's?
    tokens = nltk.tokenize.word_tokenize( clean_html )
    soup_histogram = nltk.probability.FreqDist( tokens )
    # if top words intersect with English stopwords, then consider soup for ngram_histogram
    if len( set( soup_histogram.keys()[10] ) & english_stopwords ) > 0 :
      for n in xrange( 2, ngram_limit + 1 ):
        for ngram in nltk.util.ingrams( tokens, n ):
          logging.debug( str( ngram ) )
          ngram_histogram.inc( ngram )
  except HTMLParser.HTMLParseError:
    logging.info( 'HTML cleaning failed' )

def print_ngram_histogram():
  logging.info( 'Sorted ngram histogram' )
  for item in ngram_histogram.items():
    logging.info( str( item[0] ) + ' = ' + str( item[1] ) )

def get_top_K_pages( phrase, K ):
  """
    In which we coax a mighty search engine into giving us what we want.
    TODO:
    References:
      - http://en.wikibooks.org/wiki/Python_Programming/Internet
      - http://docs.python.org/library/urllib2.html
  """
  global W, T_to_be_visited
  # TODO: use urllib.quote instead of str.replace
  search_url = yahoo_url % ( phrase.replace( ' ', '+' ), str( K ) )
  # Sleep for a few seconds, just in case we are calling the search engine too frequently
  time.sleep( search_lag_time )
  search_results = urllib2.urlopen( urllib2.Request( search_url, None, headers ) )
  clickurls = BeautifulSoup.SoupStrainer( 'clickurl' )
  results_soup = BeautifulSoup.BeautifulStoneSoup( search_results, parseOnlyThese = clickurls )
  logging.debug( 'Search results: ' + results_soup.prettify() )
  # order of W is not important at the moment
  W = set( [ link.string for link in results_soup.findAll( 'clickurl' ) ] )
  T_to_be_visited = list( W.copy() )

def get_context( link ):
  """
    In which we follow the footsteps of SMSFind. Add to affinity_set here.
  """
  pass

def crawl():
  """
    In which we follow the money.
    TODO:
      - might wanna consider a link's "name", besides in-degree and context terms, because the name might overlap a contextual term
      - ignore linked pages that are not in English or not in the <*ML> family
      - should we preserve the web graph? i don't see why we need it right now.
    References:
      - http://www.crummy.com/software/BeautifulSoup/documentation.html
  """
  global T_to_be_visited, T_visited
  logging.info( 'T_to_be_visited: ' + str( T_to_be_visited ) )
  for n in xrange( len( T_to_be_visited ) ):
    link = T_to_be_visited.pop( 0 )
    if link not in T_visited:
      logging.info( 'Getting page at ' + link )
      time.sleep( search_lag_time )
      try:
        page = urllib2.urlopen( urllib2.Request( link, None, headers ) )
        page = BeautifulSoup.BeautifulSoup( page )
        soup_to_ngrams( page, 3 )
        out_links = set( [ out_link['href'] for out_link in page.findAll( 'a' ) if out_link.has_key( 'href' ) ] )
        for out_link in out_links:
          url = urlparse.urlparse( out_link )
          # Oh, Python, how I love thee.
          if url.scheme == 'http' and url.fragment == '':
            out_link = urlparse.urljoin( link, out_link )
            if out_link not in T_visited:
              # TODO: a list does not handle redundant entries, but the T_visited check should at least prevent visiting them; think of a smarter way
              T_to_be_visited.append( out_link )
        logging.info( 'This page relatively links to: ' + str( out_links ) )
      except (urllib2.HTTPError, urllib2.URLError, UnicodeEncodeError), error:
        logging.info( 'Skipping link due to: ' + str( error ) )
      finally:
        T_visited.add( link )
    else:
      logging.info( 'Skipping visited link: ' + link )

if __name__ == '__main__':
  logging.basicConfig( level=logging.INFO, format='%(asctime)s %(levelname)-8s %(message)s', datefmt='%a, %d %b %Y %H:%M:%S', filename='crawler.log', filemode='w' )
  query_phrase = 'von neumann'
  # TODO: strip all whitespace from affinity set terms
  affinity_set = set( [ 'los', 'alamos' ] )
  for subset in powerset( list( affinity_set ) ):
    phrase = query_phrase
    for word in subset:
      phrase = phrase + ' ' + word
    logging.info( 'Querying for combination: ' + phrase )
    get_top_K_pages( phrase, 10 )
    crawl()
  for n in xrange( 1, 3 ):
    logging.info( 'Crawling T at degree ' + str( n ) )
    crawl()
  print_ngram_histogram()
