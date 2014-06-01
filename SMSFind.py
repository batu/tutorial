#!/usr/local/bin/python2.5
from urllib import FancyURLopener 
from HTMLParser import HTMLParser
import re, os, pickle, sys
from math import log10, log, sqrt
from collections import defaultdict
import pdb 

#NUMBERS = ["zero", "one", "two", "three", "four", "five", "six", "seven", "eight", "nine", "zero", 
#        "ten", "eleven", "twelve", "thirteen", "fourteen", "fifteen", "sixteen", "seventeen", "eighteen", "nineteen",
#        "twenty", "thirty", "forty", "fifty", "sixty", "seventy", "eighty", "ninety",
#        "hundred", "thousand", "million"]
TRY_NUMBERS = ["phone", "price", "date", "number", "time", "birthday", "when", "age", "many"]
COMMON_WORDS = ["the", "be", "to", "of", "and", "a", "in", "that",
        "have", "I", "it", "for", "not", "on", "with", "he", "as",
        "you", "do", "at", "this", "but", "his", "by", "from",  "they",
        "we", "say", "her", "she", "or", "an", "will", "my", "one",
        "all", "would", "there", "their", "what", "so", "up", "out",
        "if", "about", "who", "get", "which", "go", "me", "when",
        "make", "can", "like", "time", "no", "just", "him", "know",
        "take", "people", "into", "year", "your", "good", "some",
        "could", "them", "see", "other", "than", "then", "now", "look",
        "only", "come", "its", "over", "think", "also", "back", "after",
        "use", "two", "how", "our", "work", "well", "way", "even",
        "new", "want", "because", "any", "these", "give", "day", "most",
        "us", "is", "was", "e-mail", "news", "bio", "more", "less"]
GARBAGE_WORDS = ["name", "answers.com", "home page", "browse", "says", "video", "click", "anonymous", "click here", "celebrity", "answers", "answer", "categories", "page", "artists", "home", "question", "page browse", "home page browse", "posted", "ago", "movies", "yahoo", "movie", "report", "abuse", "report abuse", "jobs", "user", "rating", "words"]

#proxies = {'http': 'http://127.0.0.1:8080/'}

class myURLopener(FancyURLopener):
    version = "Mozilla/5.0 (X11; U; Linux i686; en-US; rv:1.9.0.5) Gecko/2008121622 Ubuntu/8.10 (intrepid) Firefox/3.0.5"

# read one of the ngram frequency files
def read_ngram_file(n):
    # read in the n_grams from ldc
    filename = str(n) + 'gramlowerv2.txt.clean'
    print "reading: " + filename
    fn = open(filename, 'r')
    lines = fn.readlines()
    ngrams = {}

    z = 1
    for line in lines:
        lineinfo = line.split()
        infolen = len(lineinfo)
        for term in lineinfo:
            term.strip()
        count = lineinfo[-1]
        lineinfo = lineinfo[:-1]
        entry = " ".join(lineinfo)
        ngrams[entry] = count
        z += 1
    return ngrams

# initialize the ngram frequency db
def init_ngram_freqs():
    global ngramdict
    for i in range (1, 5):
        ngramdict[i] = read_ngram_file(i)

# lookup the frequency value of the n_gram key
def lookup_freq(n_gram):
    global ngramdict
    n_gram2 = n_gram.replace("-", " - ")
    n = len(n_gram2.split())
    tempscore = 50000
    # make sure the n is covered by our dictionary
    if n == 0 or n > 4:
        pass # do nothing
    elif ngramdict[n].has_key(n_gram2):
        tempscore = int(ngramdict[n][n_gram2])
    else:
        pass #return 50000

    # normalize based on max frequencies / log-log curve fit
    tempscore = log10(tempscore - 49999)
    if n == 1:
        tempscore = tempscore / 11.0
    elif n == 2:
        tempscore = tempscore / 10.4
    elif n == 3:
        tempscore = tempscore / 9.9
    elif n == 4:
        tempscore = tempscore / 9.9
    else:
        tempscore = tempscore / 9.9
    tempscore = 1 - tempscore
    return tempscore

def classify(words):
    global pickled_dict
    ans = None
    cur_type = None
    for w in words:
        trynumber = w.replace(':', '').replace('.', '').replace(',', '').replace('/', '')
        if trynumber.isdigit():
            cur_type = "number"
#        elif w in NUMBERS:
#            cur_type = "number"
        elif w in pickled_dict:
            cur_type = "word"
        else:
            cur_type = "unknown"
        if ans != None and ans != cur_type:
            return "mixed"
        else:
            ans = cur_type
    return ans

def strip_btw_tag(s, tag):
    b = []
    e = [0]
    begin = s.find("<"+tag)
    end   = s.find("</"+tag)
    while begin != -1 and end != -1:
        b.append(begin)
        e.append(end)
        begin = s.find("<"+tag, end)
        end   = s.find("</"+tag, begin)
    b.append(-1)
    ans = ""
    for (start, stop) in zip(e, b):
        ans = ans+s[start:stop]
    return ans

# modified this in a easy way to just grab some junk too because of tag attributes
# that weren't in <cite></cite>, which was what this method was only being used for
def grab_google_result_urls(s):
    grab = []
    begintag = "<h3 class=r><a href=\"" 
    endtag = "</h3>"
    begin = s.find(begintag)
    end = s.find(endtag)
    end = s.find("\"", begin+len(begintag))
    while begin != -1 and end != -1:
        grab.append((begin, end))
        begin = s.find(begintag, end)
        end = s.find(endtag, begin)
        end = s.find("\"", begin+len(begintag))
    i = 1
    ans = {}
    for (begin, end) in grab:
        ans[s[begin+len(begintag):end]] = i
        i += 1
    return ans


def strip_tags(s):
        # replace with ". " rather than " "
        return re.sub("<[^>]*>", " ", s)

#not used
def strip_surrounding_punct(s):
    #        ans = ""
    #	# added <-=>
    #        # don't want to strip out commas and : since they're often in dates, but the way
    #        # this is currently setup, we need to strip stuff to tokenize
        punct = ":;?!/\[]{}()|<-=>\n\t\r\""
        #punct = ".,:;?!/\[]{}()|<-=>\n\t\r\""
        s = s.replace('&quot;', '\"')
        s = s.replace('&raquo;', '>>')
        s = s.replace('&laquo;', '<<')
        s = s.replace('&rsquo;', '>>')
        s = s.replace('&lsquo;', '>>')
        s = s.replace('&gt;', '>')
        s = s.replace('&lt;', '<')
        s = s.replace('&nbsp;', ' ')
        s = s.replace('&#160;', ' ')
        s = s.replace('&amp', '')
        s = s.replace('=', ' ') 
        s = s.replace('&#8217', '\'') #'
        s = s.replace('&#8226', '.') #.
        s = s.replace('&#9658', '') # right triangle
        s = s.replace('&#9660', '') # down triangle
        s = s.replace('&#39', '\'') #'
        s = s.replace('&#124', '|') #|
        s = s.replace('&#149', '') #square bullet
        s = s.replace('&#183', '') #square bullet
        s = s.replace('#', ' ') 
        #s = s.replace('--', '-')
    #        for c in s:
    #            if c not in punct:
    #                ans = ans+c
    #            else:
    #                ans = ans+' '
    #        return ans
    #
        if len(s) > 0:
            c = s[-1]
            while c in punct:
                s = s[:-1].strip()
                if len(s) > 0:
                    c = s[-1]
                else:
                    break
        if len(s) > 0:
            c = s[0]
            while c in punct:
                s = s[1:].strip()
                if len(s) > 0:
                    c = s[0]
                else:
                    break
        return s

#not used
def strip_spaces(s):
        ans = ""
        punct = "\n\t"
        s = s.replace('&nbsp;', ' ')
        s = s.replace('&#160;', ' ')
        for c in s:
            if c not in punct:
                ans = ans+c
            else:
                ans = ans+' '
        return ans

class Page:
    def __init__(self, url, mean_rank, context):
        try:
            self.url = url
            #global proxies
            infp = myURLopener().open(url)
            #remove useless or inconsequential tags
            self.s = strip_btw_tag(strip_btw_tag(strip_btw_tag(infp.read().lower(), "script"), "style"), "cite")
            self.s = self.s.replace("<b>", "")
            self.s = self.s.replace("</b>", "")
            self.s = self.s.replace("<i>", "")
            self.s = self.s.replace("</i>", "")
            self.s = self.s.replace("<strong>", "")
            self.s = self.s.replace("</strong>", "")
            self.s = self.s.replace("<em>", "")
            self.s = self.s.replace("</em>", "")
            self.s = self.s.replace("</p>", ". ")
            #self.s = self.s.replace("</title>", ". ")
            self.s = self.s.replace("</li>", ". ")
            self.s = strip_tags(self.s)
            # remove useless google results page crap 
            if self.url.startswith("http://www.google.com"):
                pos = self.s.find("seconds)")
                if pos > 0:
                    self.s = self.s[pos+len("seconds)"):]
                pos = self.s.find("filetype:pdf")
                if pos > 0:
                    self.s = self.s[pos+len("filetype:pdf)"):]
                pos = self.s.find("searches related to:")
                if pos > 0:
                    self.s = self.s[:pos]
                # JJJ: essentially blacklisted terms
                self.s = self.s.replace("cached", "")
                self.s = self.s.replace("similar", "")
                self.s = self.s.replace("google", "")
                self.s = self.s.replace("wikipedia", "")
                self.s = self.s.replace("wikianswers", "")
                self.s = self.s.replace("search", "")
                self.s = self.s.replace("results", "")
                self.s = self.s.replace("pages", "")
                self.s = self.s.replace("filetype:pdf", "")
                self.s = self.s.replace("block user", "")
            self.one_grams = self.get_one_grams(self.s)
            self.mean_rank = mean_rank
            self.context = context
            infp.close()
        except IOError:
            print "IO ERROR!"
            self.s = ""
            self.one_grams = []
            self.mean_rank = None
            self.context = ""
    def get_one_grams(self, sentence):
        one_grams = []
        tmp = sentence.split()
        for token in tmp:
            # discard empty n_grams 
            if len(token.strip()) == 0:
                continue
            # discard longer than maximum length tokens
            if len(token) >= 130:
                continue
            # discard URLs
            if token.startswith("http://"):
                continue
            token = strip_surrounding_punct(token)
            if len(token) > 0:
                one_grams.append(token)
        return one_grams
    def get_Neighborhoods(self):
        ans = set()

        # get the indices of the context term
        indices = []
        num_one_grams = len(self.one_grams)
        if num_one_grams == 0:
            return ans
        try:
            pos = self.one_grams.index(self.context)
            while True:
                indices.append(pos)
                if pos >= num_one_grams:
                    break
                pos2 = self.one_grams[pos+1:].index(self.context) + pos+1
                pos = pos2
        except ValueError:
            pass
        print indices
    
        if False:
            # XXX: version to ignore indices of context term
            left = 0
            right = 1
            while True:
                curr_one_grams = self.one_grams[left:right]
                # gather up an appropriately long chunk
                curr_chunk = " ".join(curr_one_grams)
                #pdb.set_trace()
                while right < num_one_grams - 1 and len(curr_chunk) + len(self.one_grams[right+1])+1 < 130: #+1 is for the space
                    right += 1
                    curr_one_grams = self.one_grams[left:right]
                    curr_chunk = " ".join(curr_one_grams)
                # color the indices for the chunks that have the context in it
                ans.add(Neighborhood(self.url, curr_one_grams, self.mean_rank, self.context))
                if right == num_one_grams-1:
                    break
                left += 1 

            # XXX: this is w/context to limit the neighborhoods
            ## for each index, grow out left, right up to 130 characters
            #for index in indices:
            #    left = index
            #    right = index
            #    while progress == True:
            #        progress = False
            #        curr_one_grams = self.one_grams[left:right]
            #        # gather up an appropriately long chunk
            #        curr_chunk = " ".join(curr_one_grams)
            #        if left > 0 and len(" ".join(self.one_grams[left:right])) < 130:
            #            left -= 1
            #            progress = True
            #        if right < num_one_grams - 1 and len(" ".join(self.one_grams[left:right+1])) < 130:
            #            right += 1
            #            progress = True
            #    ans.add(Neighborhood(self.url, curr_one_grams, self.mean_rank, self.context))
        elif True:
            # sentence boundary version
            puncts = '[.,:;?!/\[]{}()|\n\t\r\"]'
            import re
            chunks = re.compile('[.,?!]+')
            #pdb.set_trace()
            for sentence in chunks.split(self.s):
              curr_one_grams = []
              for one_gram in strip_surrounding_punct(sentence.lower()).split():
                curr_one_grams.append(one_gram)
              ans.add(Neighborhood(self.url, curr_one_grams, self.mean_rank, self.context))
              #print curr_one_grams
        else:
            # rather than create "sentences" based on "." splits, we should go through and get < 130 x 2 character chunks
            # that with the context term directly in the middle.
    
            #if len(self.one_grams) <= 0:
            #    return ans 
    
            # get the proper length chunk spreading on either side of each index
            coloredindices = [0]*num_one_grams
            for index in indices:
                left = index
                right = index
                progress = True 
                while progress == True:
                    progress = False
                    curr_one_grams = self.one_grams[left:right]
                    # gather up an appropriately long chunk
                    curr_chunk = " ".join(curr_one_grams)
                    if left > 0 and len(" ".join(self.one_grams[left:right])) < 130:
                        left -= 1
                        progress = True
                    if right < num_one_grams - 1 and len(" ".join(self.one_grams[left:right+1])) < 130:
                        right += 1
                        progress = True
                for i in range(left, right):
                    coloredindices[i] = 1
            # # XXX: think this code just takes contiguous chunks without trying to evenly spread around the context
            # left = 0
            # right = 1
            # while True:
            #     curr_one_grams = self.one_grams[left:right]
            #     # gather up an appropriately long chunk
            #     curr_chunk = " ".join(curr_one_grams)
            #     #pdb.set_trace()
            #     while right < num_one_grams - 1 and len(curr_chunk) + len(self.one_grams[right+1])+1 < 130: #+1 is for the space
            #         right += 1
            #         curr_one_grams = self.one_grams[left:right]
            #         curr_chunk = " ".join(curr_one_grams)
            #     # color the indices for the chunks that have the context in it
            #     if self.context in curr_one_grams:
            #         for i in range(left, right):
            #             coloredindices[i] = 1
            #         #ans.add(Neighborhood(self.url, curr_one_grams, self.mean_rank, self.context, indices))
            #     # if we're at the end
            #     if right == num_one_grams-1:
            #         break
            #     left = right

            # add the marked "Neighborhoods" of whatever length
            left = 0
            right = 1
            while True:
                # find the first left position
                while left < num_one_grams and coloredindices[left] == 0:
                    left += 1
                # no more marked indices
                if left == num_one_grams:
                    break
                right = left+1
                # find the final right position
                while right < num_one_grams and coloredindices[right] != 0:
                    right += 1
                # add this chunk
                curr_one_grams = self.one_grams[left:right]
                ans.add(Neighborhood(self.url, curr_one_grams, self.mean_rank, self.context))
                # last possible right index, quit
                if right == num_one_grams:
                    break
                left = right
        self.neighborhoods = ans
        return ans
    def load_n_grams(self, n_grams):
        n_value = 3
        if False:
            n_value = 1
        for n in self.get_Neighborhoods():
            for (s, min_dist) in n.get_n_grams(n_value):
                if s in n_grams:
                    n_grams[s].freq += 1
                    n_grams[s].mean_rank += self.mean_rank
                    #avg 
                    #if min_dist <= 8:
                        #n_grams[s].min_dist += min_dist
                    n_grams[s].min_dist = min(min_dist, n_grams[s].min_dist)
                    # added the neighborhood pointer 
                    n_grams[s].neighborhood.add(n)
                else:
                    n_grams[s] = nGramInfo(s)
                    n_grams[s].mean_rank += self.mean_rank
                    n_grams[s].min_dist = min_dist
                    # added the neighborhood pointer
                    # XXX: saw a python page that said to use union instead of add ie. "n_grams[s].neighborhood |= set([n])"
                    n_grams[s].neighborhood.add(n)

class resultsPage:
    def __init__(self, query, num_results=5):
        query = query.lower()
        self.context = query.split()[-1]
        self.query = set(query.split())
        self.num_results = num_results
        self.urls = {}
        self.n_grams = {}
        self.maxngramfreq = {}
        for i in range(0, 10):
            self.maxngramfreq[i] = 0
        url = "http://www.google.com/search?hl=en&q="+("+".join(query.split(" ")))+"+-filetype:pdf"#+"allinanchor:"+("+".join(query.split(" ")))
        # wikipedia results only
        #url = "http://www.google.com/search?hl=en&q="+("+".join(query.split(" ")[:-1]))
        #url = url + "+site%3Awikipedia.org"
        #global proxies
        infp = myURLopener().open(url)
        self.s = infp.read()
        try:
            #print url
            f = open('latestresults.html','w')
            f.write(self.s)
            f.close()
        except:
            print 'failed to download ' + url + ' to ' + filename
        #self.s = self.s[self.s.find(">", self.s.find("div id=res")):]
        #self.s = strip_tags_except(strip_btw_tag(strip_btw_tag(self.s, "style"), "script"), "cite", "")
        infp.close()
        # assign the result page to 0 rank
        self.urls[url] = 0
        self.get_urls()
    def get_urls(self):
        tmp = grab_google_result_urls(self.s)
        while len(tmp) != 0:
            (key, val) = tmp.popitem()
            # throw out youtube pages
            if key.startswith("http://www.youtube.com"):
                continue
            if val <= self.num_results:
                self.urls[key] = val
    def load_n_grams(self):
        for (key, val) in self.urls.items():
            print "\n" + key 
            Page(key, val, self.context).load_n_grams(self.n_grams)
    def clean_n_grams(self):
        self.cleaned = {}
        while len(self.n_grams) != 0:
            (key, val) = self.n_grams.popitem()
            #if key.find("malchezaar") >= 0:
            #    pdb.set_trace()
            # throw out whitespace n_grams
            if len(key.split()) == 0:
                continue
            ## drop everything from the result page
            #if val.mean_rank == 0:
            #   continue 
            ## JJJ: not doing this anymore now that we've got the ldc
            ## drop highly common words in dictionary
            ## used to be <= 2, but i felt it was too broad
            #if len(key.split()) < 2 and val.type == "word":
            #    pass
            # drop results shorter than 3 letters
            elif len(key) <= 3 and val.type != "number":
                pass
            # XXX: need more work to prevent echoing synonyms or contractions
            ## drop results with all terms in the query 
            #elif len(self.query.intersection(set(key.split()))) == len(key.split()):
            # drop garbage words
            elif key in GARBAGE_WORDS:
                pass
            # drop results with more than half the terms in the query or common words
            elif (len(set(key.split()).intersection(COMMON_WORDS)) + len(self.query.intersection(set(key.split())))) * 2 >= len(key.split()):
                pass
            # drop things that are too low frequency 
            elif val.freq <= 2:
	        pass
	    # drop things that are too far from the context
	    elif val.min_dist > 8:
	        pass
            #elif len(key.split()) > 1 and key.split()[0] == key.split()[1]:
            #    pass
            # added this to throw out words when we know we want a number
            elif len(self.query.intersection(TRY_NUMBERS)) >= 1 and val.type == "word":
                pass
            else:
                # normalize as well to [0,1]
                #info.score = freq_weight * (float(info.freq)/info.ldc_freq) + min_dist_weight * ((info.min_dist - 1)/7) + mean_rank_weight * (info.mean_rank/5) 
                val.mean_rank = 1 - (float(val.mean_rank)/val.freq)/5
                val.min_dist = 1 - (float(val.min_dist - 1))/7
                #val.freq = (float(val.freq))/self.maxngramfreqs[len(key.split())]
                #val.min_dist = float(val.min_dist/val.freq)
                val.ldc_freq = lookup_freq(key)
                self.cleaned[key] = val

                # normalize freq here, in proportion to distributions for n
                if self.maxngramfreq[len(key.split())] < val.freq:
                    self.maxngramfreq[len(key.split())] = val.freq
        # while len(cleaned) != 0:
        #     (key, val) = cleaned.popitem()
        #     self.n_grams[key] = val
    # score terms
    # subsume terms
    # filter low scores
    def subsume_and_filter(self):
        # weights and thresholds
        # currently no weights for freq, min_dist, mean_rank
        global freq_weight
        global min_dist_weight
        global mean_rank_weight
        global score_threshold

        ans = self.cleaned.items()
        # first sort by the number of terms
        ans.sort(lambda x,y: len(x[0].split())-len(y[0].split()))
        # set all bonuses to 0
        # calculate the base n_gram score
        for (result, info) in ans:
            #            info.bonus_freq = 0 
#            info.bonus_score = 0 
            # normalize min_dist so its not such a huge impact
            #info.score = float(info.freq)/(info.min_dist*((info.mean_rank+20)/20))
            # XXX: SCORING FUNCTION
            # normalize freq here, in proportion to distributions for n
            info.freq = float(info.freq) / self.maxngramfreq[len(result.split())]

            info.score = freq_weight * (float(info.freq)*info.ldc_freq) + min_dist_weight * info.min_dist + mean_rank_weight * info.mean_rank 
            #info.score = float(info.freq)/((info.min_dist + 0.001)*((info.mean_rank+10)/10) * log(info.ldc_freq))
        # subsume
        for (result1, info1) in ans:
            info1.subsumed = False
            for (result2, info2) in ans:
                if result1 == result2:
                    continue
                if result2.find(result1) >= 0:
                    info1.subsumed = True
        # get the total_freq
        for (result, info) in ans:
            info.total_freq = info.freq

        ## filtering and reweighting stuff ##
        # sort by total score 
        ans.sort(lambda x,y: cmp(y[1].score,x[1].score))
        # discard low score results for final answer
        if len(ans) == 0:
            return ans
        top_result = ans[0][0]
        top_info = ans[0][1]
        begin_discard = False
        for (result, info) in ans:
            if begin_discard == False:
                info.discarded = False
                # skip 1st
                if top_result != result:
                    if top_info.score-info.score > score_threshold * top_info.score:
                        begin_discard = True
                        info.discarded = True
            else:
                info.discarded = True

        return ans
    def sort_n_grams(self, ans):
        """Provisional."""
        #ans.sort(lambda x,y: y[1].total_freq-x[1].total_freq)
        # sort by total frequency
        ##ans.sort(lambda x,y: y[1].total_freq-x[1].total_freq)
        ## sort by mean rank
        #ans.sort(lambda x,y: cmp(x[1].mean_rank,y[1].mean_rank))
        ## sort by minimum distance
        #ans.sort(lambda x,y: x[1].min_dist-y[1].min_dist)
        return ans
    # disabled for now
    def remove_discarded(self, ans):
        final_ans = []
        for (n_gram, info) in ans:
            if info.discarded == False:
                final_ans.append([n_gram, info])
        return final_ans 
    def get_shingle_ans_spread_ver(self, hoods, shingles, ngram_ans):
        # setup a dictionary of scores
        shinglescores = {}
        for shingle in shingles:
            shinglescores[" ".join(shingle)] = 0.0
        #scoring the shingles
        for shingle in shinglescores.keys():
            for (n_gram, info) in ngram_ans:
                # only count scores for top n_grams
                #if info.discarded == True:
                #    break
                if n_gram in shingle:
                    shinglescores[shingle] += info.score
        shingle_ans = []
        for shingle in shinglescores.keys():
            shingle_ans.append((shingle, shinglescores[shingle]))
        # sort by the scores
        # what a stupid lambda to get around rounding errors
        shingle_ans.sort(lambda x,y: int((10*y[1])-(10*x[1])))

        # get a representative set of shingles rather than clumped results
        rep_shingle_ans = []
        for (shingle, score) in shingle_ans:
            for hood in hoods:
                if hood.rep == None and shingle in hood.sentence:
                    rep_shingle_ans.append((shingle, hood.url_source, score))
                    hood.rep = shingle
                    break
        return rep_shingle_ans 
    def get_shingle_ans_top_ver(self, hoods, shingles, ngram_ans):
        # setup a dictionary of scores
        shinglescores = {}
        for shingle in shingles:
            shinglescores[" ".join(shingle)] = 0
        # get the shingles
        for shingle in shinglescores.keys():
            count = 1
            for (n_gram, info) in ngram_ans:
                # only count scores for top 5 n_grams that aren't discarded
                if count > 5:
                    break
                if info.discarded == True:
                    break
                if n_gram in shingle:
                    # guaranteeing that the top contiguous results will be in the highest scoring shingles
                    shinglescores[shingle] += (2**(5 - count)) #info.score
                count += 1
        shingle_ans = []
        for shingle in shinglescores.keys():
            shingle_ans.append((shingle, shinglescores[shingle]))

        # sort by the scores 
        # what a stupid lambda to get around rounding errors 
        shingle_ans.sort(lambda x,y: y[1]-x[1])
        #shingle_ans.sort(lambda x,y: int((10*y[1])-(10*x[1])))
        
        # XXX: its not so much the hoods that need to be represented as it is the n_grams
        # the first should contain the first result, the second should contain the second etc.
        rep_shingle_ans = []
        count = 0 #offset by 1
        for (shingle, score) in shingle_ans:
            if count > 4:
                break
            if count > len(ngram_ans) - 1:
                break
            if score < (2**(5 - count)):
                #pdb.set_trace()
                modified_shingle = shingle.replace(ngram_ans[count][0], "[" + ngram_ans[count][0] + "]")
                for hood in hoods:
                    if shingle in hood.sentence:
                        rep_shingle_ans.append((modified_shingle, hood.url_source, score))
                        break
                count += 1
                continue
        return rep_shingle_ans
    def go(self):
        shingle_ans = []
        ngram_ans = []

        self.load_n_grams() # gets all the neighborhoods
        # skip any real cleaning or subsume/filtering
        if False:
            # do the tf-idf
            self.cleaned = {}
            while len(self.n_grams) != 0:
                (key, val) = self.n_grams.popitem()
                # only keep n_grams (and their associated hoods) that appear in the query
                if key in self.query:
                    self.cleaned[key] = val
            ngram_ans = self.cleaned.items()

            # get hoods
            hoods = []
            for (n_gram, info) in ngram_ans:
                for hood in info.neighborhood:
                    # gather up the neighborhoods
                    if len(hood.one_grams) > 0:
                        hoods.append(hood)

            # score hoods based on tf-idf
            D = len(hoods)
            if D > 0:
                idfcount = {} 
                tfidf_score_sum = {}
                tf_ij = defaultdict(dict)
                terms = self.query
                i = 0
                for term in terms:
                    idfcount[term] = 0
                    for hood in hoods:
                        if hood.sentence.count(term) > 0:
                            idfcount[term] += 1
                for hood in hoods:
                    for term in terms:
                        freq_count = hood.sentence.count(term)
                        hood_length = len(hood.one_grams)
                        tf_ij[term][hood.sentence] = float(freq_count) / float(hood_length)
                for hood in hoods:
                    tfidf_score_sum[hood.sentence] = 0
                    for term in terms:
                        if idfcount[term] == 0:
                            continue
                        #tfidf_score = tf_ij[term][hood.sentence] * log10(D / idfcount[term])
                        tfidf_score = tf_ij[term][hood.sentence] * (D / idfcount[term])
                        tfidf_score_sum[hood.sentence] += tfidf_score
                    shingle_ans.append((hood.sentence, hood.url_source, tfidf_score_sum[hood.sentence])) 
                shingle_ans.sort(lambda x,y: int(1000*y[2]-1000*x[2]))
        else:
            self.clean_n_grams()
            ngram_ans = self.subsume_and_filter()
            #ngram_ans = self.sort_n_grams(ngram_ans)
            print("%30s\t%10s\t%20s\t%10s\t%5s\t%7s\t%10s\t%10s" % ("n_gram", "score", "freq(base*ldc)", "min_dist", "mean_rank", "type", "subsumed", "discarded"))
            print("")
            limit = 0
            for (n_gram, info) in ngram_ans:
                print("%30s\t%7f\t(%f*%f)\t%10f\t%5f\t%7s\t%10s\t%10s" % (n_gram, info.score, info.freq, info.ldc_freq, info.min_dist, info.mean_rank, info.type, info.subsumed, info.discarded))
                limit += 1
                if limit > 50:
                    break
            # remove discarded for returning of final results
            #ans = self.remove_discarded(ans)
    
            # score the neighborhoods
            # put all the ngram answers into a bucket
            #put all the hoods into a bucket
            # iterate through the hoods
            # for each term in the hood score the word's value
            # pick the hood with the highest total value
            # need to take into account the longer than 130 byte hoods, and get max value
            shingles = []
            hoods = []
            for (n_gram, info) in ngram_ans:
                for hood in info.neighborhood:
                    # gather up the neighborhoods
                    hoods.append(hood)
                    # skip hoods with mean_rank = 0
                    #if hood.mean_rank == 0:
                    #    pass
                    # JJJ: redundant, check for the context term
                    new_shingles = get_shingles(hood.one_grams)
                    for shingle in new_shingles:
                        shingles.append(shingle)
    
            # XXX; spread vs TOP
            # spread shingles across neighborhoods or just get the ones that represent the top ngrams
            #shingle_ans = self.get_shingle_ans_top_ver(hoods, shingles, ngram_ans)
            shingle_ans = self.get_shingle_ans_spread_ver(hoods, shingles, ngram_ans)

        #return (shingle_ans, ngram_ans)
        return shingle_ans

class Neighborhood:
    def __init__(self, url_source, one_grams, mean_rank, context):
        self.url_source = url_source
        self.one_grams = one_grams
        self.sentence = " ".join(one_grams)
        self.mean_rank = mean_rank
        self.length = len(self.one_grams)
        self.score = 0
        self.rep = None 

        # gather up all the contexts indices
        self.context_i = []
        try:
	    index = self.one_grams.index(context)
            while True:
                self.context_i.append(index)     
                if index >= self.length:
                    break
                index = self.one_grams[index+1:].index(context) + index+1
        except ValueError:
            pass

        print self.one_grams
    def get_n_grams(self, max):
        global COMMON_WORDS
        ans = set()
        for n in range(1, max+1):
            for left in range(self.length-n):
                right = left+n-1
                # don't count common words
                while self.one_grams[right] in COMMON_WORDS and right < self.length-1:
                    right += 1
                tmp = " ".join(self.one_grams[left:right+1])
                # calculate the min_dist for each context occurrence
                min_dist = 999 
                for context in self.context_i:
                    # changed min dist to 1 even if the ngram includes the context term
                    min_dist = min(abs(right-context), abs(left-context), min_dist)
                    if min_dist == 0:
                        min_dist = 1
                ans.add((tmp, min_dist))
        return ans

class resultObject:
    def __init(self, shingles, ngrams):
        self.shingles = shingles
        self.ngrams = ngrams
class nGramInfo:
    def __init__(self, s):
        self.freq = 1
        self.min_dist = None
        self.type = classify(s.split())
        self.mean_rank = 0
        self.neighborhood = set()
        self.besthood = None
        self.score = 0 
    def get_top_neighborhood(self):
        return self.besthood.sentence
    def get_neighborhoods(self):
        ans = sorted(self.neighborhood)
        ans.sort(lambda x,y: x.mean_rank-y.mean_rank)
        ansstring = ''
        # figure out what neighborhood should get what score based on the query
        for hood in ans:
            if hood == self.besthood:
                ansstring += "*"
            #if hood.mean_rank != 0:
            ansstring += "(" + str(hood.mean_rank) + ")[" + str(hood.score) + "] " + hood.sentence + " -\"" + hood.url_source + "\"\n\n"
        return ansstring

# get the proper length shingles from a list of one_grams 
def get_shingles(one_grams):
    shingles = [] 
    left = 0
    right = 1
    while True:
        curr_one_grams = one_grams[left:right]
        #if len(curr_one_grams) == 0:
        curr_chunk = " ".join(curr_one_grams)
        while right < len(one_grams) - 1 and len(curr_chunk) + len(one_grams[right + 1]) + 1 < 130:
            right += 1
            curr_one_grams = one_grams[left:right]
            curr_chunk = " ".join(curr_one_grams)
        #if self.context in curr_one_grams:
        shingles.append(curr_one_grams)
        if right == len(one_grams) - 1:
            break
        left += 1
    return shingles 


freq_weight = 0.50
min_dist_weight = 0.30
mean_rank_weight = 0.20
score_threshold = 0.20

pickled_dict = {}
ngramdict = {}
def set_weights(a, b, c, d):
    # set the weights based on user input
    freq_weight = a
    min_dist_weight = b 
    mean_rank_weight = c 
    score_threshold = d  
 
def setup():
    init_ngram_freqs()
    infp = open("words")
    pickled_dict = pickle.load(infp)
    infp.close()

if __name__ == "__main__":
    if len(sys.argv) <= 6:
    #if len(sys.argv) != 6:
        #print("usage: %s {query}" % sys.argv[0])
        print("usage: %s {freq_weight} {min_dist_weight} {mean_rank_weight} {score_threshold} {query...}" % sys.argv[0])
        exit()

    # start stuff
    set_weights(float(sys.argv[1]), float(sys.argv[2]), float(sys.argv[3]), float(sys.argv[4]))
    setup()
#refactored into setup
#    init_ngram_freqs()
#    infp = open("words")
#    pickled_dict = pickle.load(infp)
#    infp.close()
    rp = resultsPage(" ".join(sys.argv[5:]))
    ans = rp.go()
    # get the top answer
    result = ''
    print ""
    limit = 1
    for (shingle, url, score) in ans[0]:
        url = url.replace("http://", "")
        pos = url.find("/")
        if pos >= 0:
            url = url[:pos]
        print "[" + shingle + "] " + "(" + str(score) + ") -\"" + url + "\"\n"
        if limit >= 5:
            break
        limit += 1
    print ""
    limit = 1
    for (ngram, info) in ans[1]:
        print "[" + ngram + "] " + "(" + str(info.score) + ")\n"
        if limit >= 5:
            break
        limit += 1

    #for (n_gram, info) in ans:
    #    # get the surrounding neighborhood
    #    result = n_gram
    #    print "[" + result + "]"
    #    print info.get_neighborhoods()
    #    print ""
    exit()

