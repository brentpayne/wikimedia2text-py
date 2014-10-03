#!/usr/bin/python
# -*- coding: utf-8 -*-

"""
The this holds the code for converting wikimedia formatted strings into raw text.
This removes all special formatting and where possible converts formatting into
 the appropriate unicode characters.  Italics, bold, and other font formatting
 will be lost.  Tables and graphics will either be ignored or returned as garbage.

This is open source, if you need it build it.  I'll merge the pull requests.

The framer's intent was to convert wikipedia documents downloaded in bulk into
 raw text for input into NLP processes.  This is a necessary piece of that pipeline.

The code in this file is heavily inspired and in large part copied from the WikiExtractor.py
 project (http://medialab.di.unipi.it/Project/SemaWiki/Tools/WikiExtractor.py).
 That project like this project is under the GPLv3 license.

"""

# A copy of the WikiExtractor.py license
# =============================================================================
# Version: 2.6 (Oct 14, 2013)
#  Author: Giuseppe Attardi (attardi@di.unipi.it), University of Pisa
#	   Antonio Fuschetto (fuschett@di.unipi.it), University of Pisa
#
#  Contributors:
#	Leonardo Souza (lsouza@amtera.com.br)
#	Juan Manuel Caicedo (juan@cavorite.com)
#	Humberto Pereira (begini@gmail.com)
#	Siegfried-A. Gevatter (siegfried@gevatter.com)
#	Pedro Assis (pedroh2306@gmail.com)
#
# =============================================================================
#  Copyright (c) 2009. Giuseppe Attardi (attardi@di.unipi.it).
# =============================================================================
#  This file is part of Tanl.
#
#  Tanl is free software; you can redistribute it and/or modify it
#  under the terms of the GNU General Public License, version 3,
#  as published by the Free Software Foundation.
#
#  Tanl is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with this program.  If not, see <http://www.gnu.org/licenses/>.
# =============================================================================
import re
from htmlentitydefs import name2codepoint


def parse(text):
    """
    Give wikimedia formatted text and transform it into unicode text without any formatting.
    :param text: wikimedia formatted text
    :return: the "best" unicode representation of the wikimedia text
    """
    return u"\n".join(compact(clean(text.decode('utf-8'))))
##
# Recognize only these namespaces
# w: Internal links to the Wikipedia
# wiktionary: Wiki dictionry
# wikt: shortcut for Wikctionry
#
acceptedNamespaces = set(['w', 'wiktionary', 'wikt'])

##
# Drop these elements from article text
#
discardElements = set([
    'gallery', 'timeline', 'noinclude', 'pre',
    'table', 'tr', 'td', 'th', 'caption',
    'form', 'input', 'select', 'option', 'textarea',
    'ul', 'li', 'ol', 'dl', 'dt', 'dd', 'menu', 'dir',
    'ref', 'references', 'img', 'imagemap', 'source'
])

#=========================================================================
#
# MediaWiki Markup Grammar

# Template = "{{" [ "msg:" | "msgnw:" ] PageName { "|" [ ParameterName "=" AnyText | AnyText ] } "}}" ;
# Extension = "<" ? extension ? ">" AnyText "</" ? extension ? ">" ;
# NoWiki = "<nowiki />" | "<nowiki>" ( InlineText | BlockText ) "</nowiki>" ;
# Parameter = "{{{" ParameterName { Parameter } [ "|" { AnyText | Parameter } ] "}}}" ;
# Comment = "<!--" InlineText "-->" | "<!--" BlockText "//-->" ;
#
# ParameterName = ? uppercase, lowercase, numbers, no spaces, some special chars ? ;
#
#===========================================================================

# Program version
version = '2.5'

# A matching function for nested expressions, e.g. namespaces and tables.
def dropNested(text, openDelim, closeDelim):
    openRE = re.compile(openDelim)
    closeRE = re.compile(closeDelim)
    # partition text in separate blocks { } { }
    matches = []  # pairs (s, e) for each partition
    nest = 0  # nesting level
    start = openRE.search(text, 0)
    if not start:
        return text
    end = closeRE.search(text, start.end())
    next = start
    while end:
        next = openRE.search(text, next.end())
        if not next:  # termination
            while nest:  # close all pending
                nest -= 1
                end0 = closeRE.search(text, end.end())
                if end0:
                    end = end0
                else:
                    break
            matches.append((start.start(), end.end()))
            break
        while end.end() < next.start():
            # { } {
            if nest:
                nest -= 1
                # try closing more
                last = end.end()
                end = closeRE.search(text, end.end())
                if not end:  # unbalanced
                    if matches:
                        span = (matches[0][0], last)
                    else:
                        span = (start.start(), last)
                    matches = [span]
                    break
            else:
                matches.append((start.start(), end.end()))
                # advance start, find next close
                start = next
                end = closeRE.search(text, next.end())
                break  # { }
        if next != start:
            # { { }
            nest += 1
    # collect text outside partitions
    res = ''
    start = 0
    for s, e in matches:
        res += text[start:s]
        start = e
    res += text[start:]
    return res


def dropSpans(matches, text):
    """Drop from text the blocks identified in matches"""
    matches.sort()
    res = ''
    start = 0
    for s, e in matches:
        res += text[start:s]
        start = e
    res += text[start:]
    return res

# Match interwiki links, | separates parameters.
# First parameter is displayed, also trailing concatenated text included
# in display, e.g. s for plural).
#
# Can be nested [[File:..|..[[..]]..|..]], [[Category:...]], etc.
# We first expand inner ones, than remove enclosing ones.
#
wikiLink = re.compile(r'\[\[([^[]*?)(?:\|([^[]*?))?\]\](\w*)')

parametrizedLink = re.compile(r'\[\[.*?\]\]')

# Match HTML comments
comment = re.compile(r'<!--.*?-->', re.DOTALL)

# Match external links (space separates second optional parameter)
externalLink = re.compile(r'\[\w+.*? (.*?)\]')
externalLinkNoAnchor = re.compile(r'\[\w+[&\]]*\]')

# Titles
title = re.compile

# Matches bold/italic
bold_italic = re.compile(r"'''''([^']*?)'''''")
bold = re.compile(r"'''(.*?)'''")
italic_quote = re.compile(r"''\"(.*?)\"''")
italic = re.compile(r"''([^']*)''")
quote_quote = re.compile(r'""(.*?)""')

# Matches space
spaces = re.compile(r' {2,}')

# Matches dots
dots = re.compile(r'\.{4,}')

selfClosingTags = ['br', 'hr', 'nobr', 'ref', 'references']

# handle 'a' separetely, depending on keepLinks
ignoredTags = [
    'b', 'big', 'blockquote', 'center', 'cite', 'div', 'em',
    'font', 'h1', 'h2', 'h3', 'h4', 'hiero', 'i', 'kbd', 'nowiki',
    'p', 'plaintext', 's', 'small', 'span', 'strike', 'strong',
    'sub', 'sup', 'tt', 'u', 'var',
]

placeholder_tags = {'math': 'formula', 'code': 'codice'}


# Match elements to ignore
discard_element_patterns = [re.compile(r'<\s*%s\b[^>]*>.*?<\s*/\s*%s>' % (tag, tag), re.DOTALL | re.IGNORECASE) for tag in discardElements]


# Match ignored tags
def ignoreTag(tag):
    left = re.compile(r'<\s*%s\b[^>]*>' % tag, re.IGNORECASE)
    right = re.compile(r'<\s*/\s*%s>' % tag, re.IGNORECASE)
    return left, right

ignored_tag_patterns = [ignoreTag(tag) for tag in ignoredTags]


# Match selfClosing HTML tags
selfClosing_tag_patterns = [re.compile(r'<\s*%s\b[^/]*/\s*>' % tag, re.DOTALL | re.IGNORECASE) for tag in selfClosingTags]


# Match HTML placeholder tags
placeholder_tag_patterns = [(re.compile(r'<\s*%s(\s*| [^>]+?)>.*?<\s*/\s*%s\s*>' % (tag, tag), re.DOTALL | re.IGNORECASE), repl) for tag, repl in placeholder_tags.items()]

# Match preformatted lines
preformatted = re.compile(r'^ .*?$', re.MULTILINE)


# Function applied to wikiLinks
def make_anchor_tag(match, keep_links=False):
    link = match.group(1)
    colon = link.find(':')
    if colon > 0 and link[:colon] not in acceptedNamespaces:
        return ''
    trail = match.group(3)
    anchor = match.group(2)
    if not anchor:
        anchor = link
    anchor += trail
    if keep_links:
        return '<a href="%s">%s</a>' % (link, anchor)
    else:
        return anchor


def clean(text):
    # FIXME: templates should be expanded
    # Drop transclusions (template, parser functions)
    # See: http://www.mediawiki.org/wiki/Help:Templates
    text = dropNested(text, r'{{', r'}}')

    # Drop tables
    text = dropNested(text, r'{\|', r'\|}')

    # Expand links
    text = wikiLink.sub(make_anchor_tag, text)
    # Drop all remaining ones
    text = parametrizedLink.sub('', text)

    # Handle external links
    text = externalLink.sub(r'\1', text)
    text = externalLinkNoAnchor.sub('', text)

    # Handle bold/italic/quote
    text = bold_italic.sub(r'\1', text)
    text = bold.sub(r'\1', text)
    text = italic_quote.sub(r'&quot;\1&quot;', text)
    text = italic.sub(r'&quot;\1&quot;', text)
    text = quote_quote.sub(r'\1', text)
    text = text.replace("'''", '').replace("''", '&quot;')

    ################ Process HTML ###############

    # turn into HTML
    text = unescape(text)
    # do it again (&amp;nbsp;)
    text = unescape(text)

    # Collect spans

    matches = []
    # Drop HTML comments
    for m in comment.finditer(text):
        matches.append((m.start(), m.end()))

    # Drop self-closing tags
    for pattern in selfClosing_tag_patterns:
        for m in pattern.finditer(text):
            matches.append((m.start(), m.end()))

    # Drop ignored tags
    for left, right in ignored_tag_patterns:
        for m in left.finditer(text):
            matches.append((m.start(), m.end()))
        for m in right.finditer(text):
            matches.append((m.start(), m.end()))

    # Bulk remove all spans
    text = dropSpans(matches, text)

    # Cannot use dropSpan on these since they may be nested
    # Drop discarded elements
    for pattern in discard_element_patterns:
        text = pattern.sub('', text)

    # Expand placeholders
    for pattern, placeholder in placeholder_tag_patterns:
        index = 1
        for match in pattern.finditer(text):
            text = text.replace(match.group(), '%s_%d' % (placeholder, index))
            index += 1

    text = text.replace('<<', u'«').replace('>>', u'»')

    #############################################

    # Drop preformatted
    # This can't be done before since it may remove tags
    text = preformatted.sub('', text)

    # Cleanup text
    text = text.replace('\t', ' ')
    text = spaces.sub(' ', text)
    text = dots.sub('...', text)
    text = re.sub(u' (,:\.\)\]»)', r'\1', text)
    text = re.sub(u'(\[\(«) ', r'\1', text)
    text = re.sub(r'\n\W+?\n', '\n', text) # lines with only punctuations
    text = text.replace(',,', ',').replace(',.', '.')
    return text


##
# Removes HTML or XML character references and entities from a text string.
#
# @param text The HTML (or XML) source text.
# @return The plain text, as a Unicode string, if necessary.

def unescape(text):
    def fixup(m):
        text = m.group(0)
        code = m.group(1)
        try:
            if text[1] == "#":  # character reference
                if text[2] == "x":
                    return unichr(int(code[1:], 16))
                else:
                    return unichr(int(code))
            else:  # named entity
                return unichr(name2codepoint[code])
        except:
            return text  # leave as is

    return re.sub("&#?(\w+);", fixup, text)

section = re.compile(r'(==+)\s*(.*?)\s*\1')

def compact(text, keep_sections=False):
    """Deal with headers, lists, empty sections, residuals of tables"""
    page = []                   # list of paragraph
    headers = {}                # Headers for unfilled sections
    empty_section = False        # empty sections are discarded

    for line in text.split('\n'):

        if not line:
            continue
        # Handle section titles
        m = section.match(line)
        if m:
            title = m.group(2)
            lev = len(m.group(1))
            if keep_sections:
                page.append("<h%d>%s</h%d>" % (lev, title, lev))
            if title and title[-1] not in '!?':
                title += '.'
            headers[lev] = title
            # drop previous headers
            for i in headers.keys():
                if i > lev:
                    del headers[i]
            empty_section = True
            continue
        # Handle page title
        if line.startswith('++'):
            title = line[2:-2]
            if title:
                if title[-1] not in '!?':
                    title += '.'
                page.append(title)
        # handle lists
        elif line[0] in '*#:;':
            if keep_sections:
                page.append("<li>%s</li>" % line[1:])
            else:
                continue
        # Drop residuals of lists
        elif line[0] in '{|' or line[-1] in '}':
            continue
        # Drop irrelevant lines
        elif (line[0] == '(' and line[-1] == ')') or line.strip('.-') == '':
            continue
        elif len(headers):
            items = headers.items()
            items.sort()
            for (i, v) in items:
                page.append(v)
            headers.clear()
            page.append(line)   # first line
            empty_section = False
        elif not empty_section:
            page.append(line)

    return page


if __name__ == '__main__':
    txt = """
{{Use British English|date=January 2014}}
{{pp-move-indef}}
{{Anarchism sidebar}}

'''Anarchism''' is a [[political philosophy]] that advocates [[stateless society|stateless societies]] often defined as [[self-governance|self-governed]] voluntary institutions,&lt;ref&gt;&quot;ANARCHISM, a social philosophy that rejects authoritarian government and maintains that voluntary institutions are best suited to express man's natural social tendencies.&quot; George Woodcock. &quot;Anarchism&quot; at The Encyclopedia of Philosophy&lt;/ref&gt;&lt;ref&gt;&quot;In a society developed on these lines, the voluntary associations which already now begin to cover all the fields of human activity would take a still greater extension so as to substitute themselves for the state in all its functions.&quot; [http://www.theanarchistlibrary.org/HTML/Petr_Kropotkin___Anarchism__from_the_Encyclopaedia_Britannica.html Peter Kropotkin. &quot;Anarchism&quot; from the Encyclopædia Britannica]&lt;/ref&gt;&lt;ref&gt;&quot;Anarchism.&quot; The Shorter Routledge Encyclopedia of Philosophy. 2005. p. 14 &quot;Anarchism is the view that a society without the state, or government, is both possible and desirable.&quot;&lt;/ref&gt;&lt;ref&gt;Sheehan, Sean. Anarchism, London: Reaktion Books Ltd., 2004. p. 85&lt;/ref&gt; but that several authors have defined as more specific institutions based on non-[[Hierarchy|hierarchical]] [[Free association (communism and anarchism)|free associations]].&lt;ref&gt;&quot;as many anarchists have stressed, it is not government as such that they find objectionable, but the hierarchical forms of government associated with the nation state.&quot; Judith Suissa. ''Anarchism and Education: a Philosophical Perspective''. Routledge. New York. 2006. p. 7&lt;/ref&gt;&lt;ref name=&quot;iaf-ifa.org&quot;/&gt;&lt;ref&gt;&quot;That is why Anarchy, when it works to destroy authority in all its aspects, when it demands the abrogation of laws and the abolition of the mechanism that serves to impose them, when it refuses all hierarchical organisation and preaches free agreement — at the same time strives to maintain and enlarge the precious kernel of social customs without which no human or animal society can exist.&quot; [[Peter Kropotkin]]. [http://www.theanarchistlibrary.org/HTML/Petr_Kropotkin__Anarchism__its_philosophy_and_ideal.html Anarchism: its philosophy and ideal]&lt;/ref&gt;&lt;ref&gt;&quot;anarchists are opposed to irrational (e.g., illegitimate) authority, in other words, hierarchy — hierarchy being the institutionalisation of authority within a society.&quot; [http://www.theanarchistlibrary.org/HTML/The_Anarchist_FAQ_Editorial_Collective__An_Anarchist_FAQ__03_17_.html#toc2 &quot;B.1 Why are anarchists against authority and hierarchy?&quot;] in [[An Anarchist FAQ]]&lt;/ref&gt; Anarchism holds the [[state (polity)|state]] to be undesirable, unnecessary, or harmful.&lt;ref name=&quot;definition&quot;&gt;
{{cite journal |last=Malatesta|first=Errico|title=Towards Anarchism|journal=MAN!|publisher=International Group of San Francisco|location=Los Angeles|oclc=3930443|url=http://www.marxists.org/archive/malatesta/1930s/xx/toanarchy.htm|archiveurl=http://web.archive.org/web/20121107221404/http://marxists.org/archive/malatesta/1930s/xx/toanarchy.htm|archivedate=7 November 2012 |deadurl=no|authorlink=Errico Malatesta |ref=harv}}
{{cite journal |url=http://www.theglobeandmail.com/servlet/story/RTGAM.20070514.wxlanarchist14/BNStory/lifeWork/home/
|archiveurl=http://web.archive.org/web/20070516094548/http://www.theglobeandmail.com/servlet/story/RTGAM.20070514.wxlanarchist14/BNStory/lifeWork/home |archivedate=16 May 2007 |deadurl=yes |title=Working for The Man |journal=[[The Globe and Mail]] |accessdate=14 April 2008 |last=Agrell |first=Siri |date=14 May 2007 |ref=harv }}
{{cite web |url=http://www.britannica.com/eb/article-9117285|title=Anarchism|year=2006|work=Encyclopædia Britannica|publisher=Encyclopædia Britannica Premium Service|accessdate=29 August 2006| archiveurl= http://web.archive.org/web/20061214085638/http://www.britannica.com/eb/article-9117285| archivedate= 14 December 2006&lt;!--Added by DASHBot--&gt;}}
{{cite journal |year=2005|title=Anarchism|journal=The Shorter [[Routledge Encyclopedia of Philosophy]]|page=14|quote=Anarchism is the view that a society without the state, or government, is both possible and desirable. |ref=harv}}
The following sources cite anarchism as a political philosophy:
{{cite book | last = Mclaughlin | first = Paul | title = Anarchism and Authority | publisher = Ashgate | location = Aldershot | year = 2007 | isbn = 0-7546-6196-2 |page=59}}
{{cite book | last = Johnston | first = R. | title = The Dictionary of Human Geography | publisher = Blackwell Publishers | location = Cambridge | year = 2000 | isbn = 0-631-20561-6 |page=24}}&lt;/ref&gt;&lt;ref name=slevin&gt;Slevin, Carl. &quot;Anarchism.&quot; ''The Concise Oxford Dictionary of Politics''. Ed. Iain McLean and Alistair McMillan. Oxford University Press, 2003.&lt;/ref&gt; While anti-statism is central, some argue&lt;ref&gt;&quot;Anarchists do reject the state, as we will see. But to claim that this central aspect of anarchism is definitive is to sell anarchism short.&quot;[http://books.google.com.ec/books?id=kkj5i3CeGbQC&amp;printsec=frontcover#v=onepage&amp;q&amp;f=false ''Anarchism and Authority: A Philosophical Introduction to Classical Anarchism'' by Paul McLaughlin. AshGate. 2007. p. 28]&lt;/ref&gt; that anarchism entails opposing [[authority]] or [[hierarchical organisation]] in the conduct of human relations, including, but not limited to, the state system.&lt;ref name=&quot;iaf-ifa.org&quot;&gt;{{cite web |url=http://www.iaf-ifa.org/principles/english.html |title=IAF principles |publisher=[[International of Anarchist Federations]] |archiveurl=http://web.archive.org/web/20120105095946/http://www.iaf-ifa.org/principles/english.html |archivedate=5 January 2012 |deadurl=yes |quote=The IAF – IFA fights for : the abolition of all forms of authority whether economical, political, social, religious, cultural or sexual.}}&lt;/ref&gt;&lt;ref&gt;&quot;My use of the word hierarchy in the subtitle of this work is meant to be provocative. There is a strong theoretical need to contrast hierarchy with the more widespread use of the words class and State; careless use of these terms can produce a dangerous simplification of social reality. To use the words hierarchy, class, and State interchangeably, as many social theorists do, is insidious and obscurantist. This practice, in the name of a &quot;classless&quot; or &quot;libertarian&quot; society, could easily conceal the existence of hierarchical relationships and a hierarchical sensibility, both of which-even in the absence of economic exploitation or political coercion-would serve to perpetuate unfreedom.&quot; [[Murray Bookchin]]. ''The Ecology of Freedom: the memergence and dissolution of Hierarchy. CHESHIRE BOOKS
Palo Alto. 1982. Pg. 3'' &lt;/ref&gt;&lt;ref&gt;&quot;Authority is defined in terms of the right to exercise social control (as explored in the &quot;sociology of power&quot;) and the correlative duty to obey (as explored in the &quot;philosophy of practical reason&quot;). Anarchism is distinguished, philosophically, by its scepticism towards such moral relations – by its questioning of the claims made for such normative power – and, practically, by its challenge to those &quot;authoritative&quot; powers which cannot justify their claims and which are therefore deemed illegitimate or without moral foundation.&quot;[http://books.google.com.ec/books?id=kkj5i3CeGbQC&amp;printsec=frontcover#v=onepage&amp;q&amp;f=false ''Anarchism and Authority: A Philosophical Introduction to Classical Anarchism'' by Paul McLaughlin. AshGate. 2007. p. 1]&lt;/ref&gt;&lt;ref&gt;&quot;Anarchism, then, really stands for the liberation of the human mind from the dominion of religion; the liberation of the human body from the dominion of property; liberation from the shackles and restraint of government. Anarchism stands for a social order based on the free grouping of individuals for the purpose of producing real social wealth; an order that will guarantee to every human being free access to the earth and full enjoyment of the necessities of life, according to individual desires, tastes, and inclinations.&quot; [[Emma Goldman]]. &quot;What it Really Stands for Anarchy&quot; in ''[[Anarchism and Other Essays]]''.&lt;/ref&gt;&lt;ref&gt;Individualist anarchist Benjamin Tucker defined anarchism as opposition to authority as follows &quot;They found that they must turn either to the right or to the left, – follow either the path of Authority or the path of Liberty. Marx went one way; Warren and Proudhon the other. Thus were born State Socialism and Anarchism&amp;nbsp;... Authority, takes many shapes, but, broadly speaking, her enemies divide themselves into three classes: first, those who abhor her both as a means and as an end of progress, opposing her openly, avowedly, sincerely, consistently, universally; second, those who profess to believe in her as a means of progress, but who accept her only so far as they think she will subserve their own selfish interests, denying her and her blessings to the rest of the world; third, those who distrust her as a means of progress, believing in her only as an end to be obtained by first trampling upon, violating, and outraging her. These three phases of opposition to Liberty are met in almost every sphere of thought and human activity. Good representatives of the first are seen in the Catholic Church and the Russian autocracy; of the second, in the Protestant Church and the Manchester school of politics and political economy; of the third, in the atheism of Gambetta and the socialism of Karl Marx.&quot; [[Benjamin Tucker]]. [http://www.theanarchistlibrary.org/HTML/Benjamin_Tucker__Individual_Liberty.html ''Individual Liberty.'']&lt;/ref&gt;&lt;ref name=&quot;Ward 1966&quot;&gt;{{cite web |url=http://www.panarchy.org/ward/organization.1966.html|last=Ward|first=Colin|year=1966|title=Anarchism as a Theory of Organization|accessdate=1 March 2010| archiveurl= http://web.archive.org/web/20100325081119/http://www.panarchy.org/ward/organization.1966.html| archivedate= 25 March 2010&lt;!--Added by DASHBot--&gt;}}&lt;/ref&gt;&lt;ref&gt;Anarchist historian [[George Woodcock]] report of [[Mikhail Bakunin]]'s anti-authoritarianism and shows opposition to both state and non-state forms of authority as follows: &quot;All anarchists deny authority; many of them fight against it.&quot; (p. 9)&amp;nbsp;... Bakunin did not convert the League's central committee to his full program, but he did persuade them to accept a remarkably radical recommendation to the Berne Congress of September 1868, demanding economic equality and implicitly attacking authority in both Church and State.&quot;&lt;/ref&gt;&lt;ref&gt;{{cite book |last=Brown |first=L. Susan |chapter=Anarchism as a Political Philosophy of Existential Individualism: Implications for Feminism |title=The Politics of Individualism: Liberalism, Liberal Feminism and Anarchism |publisher=Black Rose Books Ltd. Publishing |year= 2002 |page=106}}&lt;/ref&gt;

As a subtle and anti-dogmatic philosophy, anarchism draws on many currents of thought and strategy. Anarchism does not offer a fixed body of doctrine from a single particular world view, instead fluxing and flowing as a philosophy.&lt;ref&gt;{{cite book |last=Marshall|first=Peter|title=Demands The Impossible: A History Of Anarchism|year=2010|publisher=PM Press|location=Oakland, CA|isbn=978-1-60486-064-1|pages=16}}&lt;/ref&gt; There are many types and traditions of anarchism, not all of which are mutually exclusive.&lt;ref&gt;{{cite book |last=Sylvan |first=Richard |chapter=Anarchism |title=A Companion to Contemporary Political Philosophy |editors=Goodwin, Robert E. and Pettit |publisher=Philip. Blackwell Publishing |year=1995 |page=231}}&lt;/ref&gt; [[Anarchist schools of thought]] can differ fundamentally, supporting anything from extreme [[individualism]] to complete collectivism.&lt;ref name=slevin/&gt; Strains of anarchism have often been divided into the categories of [[social anarchism|social]] and [[individualist anarchism]] or similar dual classifications.&lt;ref name=&quot;black dict&quot;&gt;[[Geoffrey Ostergaard|Ostergaard, Geoffrey]]. &quot;Anarchism&quot;. ''The Blackwell Dictionary of Modern Social Thought''. Blackwell Publishing. p. 14.&lt;/ref&gt;&lt;ref name=socind&gt;{{cite book |authorlink=Peter Kropotkin |last=Kropotkin |first=Peter |title=Anarchism: A Collection of Revolutionary Writings |publisher=Courier Dover Publications |year=2002 |page=5|isbn=0-486-41955-X}}{{cite journal |author=R.B. Fowler|title=The Anarchist Tradition of Political Thought|year=1972|journal=Western Political Quarterly|volume=25|issue=4|pages=738–752|doi=10.2307/446800|publisher=University of Utah|jstor=446800 |ref=harv}}&lt;/ref&gt; Anarchism is usually considered a radical left-wing ideology,&lt;ref name=brooks&gt;{{cite book |quote=Usually considered to be an extreme left-wing ideology, anarchism has always included a significant strain of radical individualism, from the hyperrationalism of Godwin, to the egoism of Stirner, to the libertarians and anarcho-capitalists of today |last=Brooks |first=Frank H. |year=1994 |title=The Individualist Anarchists: An Anthology of Liberty (1881–1908) |publisher=Transaction Publishers |page=xi|isbn=1-56000-132-1}}&lt;/ref&gt;&lt;ref&gt;{{cite journal |author=Joseph Kahn|title= Anarchism, the Creed That Won't Stay Dead; The Spread of World Capitalism Resurrects a Long-Dormant Movement |year=2000|journal=[[The New York Times]]|issue=5 August |ref=harv}}{{cite journal |author=Colin Moynihan |title=Book Fair Unites Anarchists. In Spirit, Anyway|year=2007|journal=New York Times|issue=16 April |ref=harv}}&lt;/ref&gt; and much of [[anarchist economics]] and [[anarchist law|anarchist legal philosophy]] reflect [[Libertarian socialism|anti-authoritarian interpretations]] of [[anarcho-communism|communism]], [[collectivist anarchism|collectivism]], [[anarcho-syndicalism|syndicalism]], [[Mutualism (economic theory)|mutualism]], or [[participatory economics]].&lt;ref&gt;&quot;The anarchists were unanimous in subjecting authoritarian socialism to a barrage of severe criticism. At the time when they made violent and satirical attacks these were not entirely well founded, for those to whom they were addressed were either primitive or “vulgar” communists, whose thought had not yet been fertilized by Marxist humanism, or else, in the case of Marx and Engels themselves, were not as set on authority and state control as the anarchists made out.&quot; Daniel Guerin, ''[http://theanarchistlibrary.org/library/daniel-guerin-anarchism-from-theory-to-practice#toc2 Anarchism: From Theory to Practice]'' (New York: Monthly Review Press, 1970)&lt;/ref&gt;

The central tendency of anarchism as a social movement has been represented by [[Anarchist communism|anarcho-communism]] and [[anarcho-syndicalism]], with [[individualist anarchism]] being primarily a literary phenomenon&lt;ref&gt;[[Alexandre Skirda|Skirda, Alexandre]]. ''Facing the Enemy: A History of Anarchist Organization from Proudhon to May 1968''. AK Press, 2002, p. 191.&lt;/ref&gt; which nevertheless did have an impact on the bigger currents&lt;ref&gt;Catalan historian Xavier Diez reports that the Spanish individualist anarchist press was widely read by members of [[anarcho-communist]] groups and by members of the [[anarcho-syndicalist]] trade union [[Confederación Nacional del Trabajo|CNT]]. There were also the cases of prominent individualist anarchists such as [[Federico Urales]] and [[Miguel Gimenez Igualada]] who were members of the [[Confederación Nacional del Trabajo|CNT]] and J. Elizalde who was a founding member and first secretary of the [[Iberian Anarchist Federation]]. Xavier Diez. ''El anarquismo individualista en España: 1923–1938.'' ISBN 978-84-96044-87-6&lt;/ref&gt; and individualists have also participated in large anarchist organisations.&lt;ref&gt;&lt;!--The exact location of this excerpt should be added to the reference.--&gt;{{cite web |url=http://web.archive.org/web/20070930014916/http://public.federation-anarchiste.org/IMG/pdf/Cedric_Guerin_Histoire_du_mvt_libertaire_1950_1970.pdf |title=Pensée et action des anarchistes en France: 1950–1970 |last=Guérin |first=Cédric |page= |pages= |at= |language=French |archiveurl=http://web.archive.org/web/20070930014916/http://public.federation-anarchiste.org/IMG/pdf/Cedric_Guerin_Histoire_du_mvt_libertaire_1950_1970.pdf |archivedate=30 September 2007 |deadurl=yes |quote=Within the [[Synthesis anarchism|synthesist]] anarchist organisation, the [[Fédération Anarchiste]], there existed an individualist anarchist tendency alongside anarcho-communist and anarchosyndicalist currents. Individualist anarchists participating inside the [[Fédération Anarchiste]] included [[Charles-Auguste Bontemps]], Georges Vincey and André Arru.}}&lt;/ref&gt;&lt;ref&gt;In Italy in 1945, during the Founding Congress of the [[Italian Anarchist Federation]], there was a group of individualist anarchists led by Cesare Zaccaria who was an important anarchist of the time.[http://www.katesharpleylibrary.net/73n6nh Cesare Zaccaria (19 August 1897 – October 1961) by Pier Carlo Masini and Paul Sharkey]&lt;/ref&gt; Many anarchists oppose all forms of aggression, supporting [[self-defense]] or [[non-violence]] ([[anarcho-pacifism]]),&lt;ref name=&quot;ppu.org.uk&quot;&gt;{{cite web |url=http://www.ppu.org.uk/e_publications/dd-trad8.html#anarch%20and%20violence |title=&quot;Resisting the Nation State, the pacifist and anarchist tradition&quot; by Geoffrey Ostergaard |publisher=Ppu.org.uk |date=6 August 1945 |accessdate=20 September 2010}}&lt;/ref&gt;&lt;ref name=&quot;Anarchism 1962&quot;&gt;[[George Woodcock]]. ''Anarchism: A History of Libertarian Ideas and Movements'' (1962)&lt;/ref&gt; while others have supported the use of some [[coercion|coercive]] measures, including violent revolution and [[propaganda of the deed]], on the path to an anarchist society.&lt;ref&gt;Fowler, R.B. &quot;The Anarchist Tradition of Political Thought.&quot; ''The Western Political Quarterly'', Vol. 25, No. 4. (December 1972), pp. 743–44.&lt;/ref&gt;

==Etymology and terminology==
{{Related articles|Anarchist terminology}}

The term ''[[wikt:anarchism|anarchism]]'' is a compound word composed from the word ''[[anarchy]]'' and the suffix ''[[-ism]]'',&lt;ref&gt;[http://www.etymonline.com/index.php?term=anarchism&amp;allowed_in_frame=0 Anarchism], [[Online etymology dictionary]].&lt;/ref&gt; themselves derived respectively from the Greek {{lang|grc|ἀναρχία}}, i.e. ''anarchy''&lt;ref&gt;{{LSJ|a)narxi/a|ἀναρχία|ref}}.&lt;/ref&gt;&lt;ref&gt;[http://www.merriam-webster.com/dictionary/anarchy Anarchy], [[Merriam-Webster]] online.&lt;/ref&gt;&lt;ref&gt;[http://www.etymonline.com/index.php?term=anarchy&amp;allowed_in_frame=0 Anarchy], [[Online etymology dictionary]].&lt;/ref&gt; (from {{lang|grc|ἄναρχος}}, ''anarchos'', meaning &quot;one without rulers&quot;;&lt;ref&gt;{{LSJ|a)/narxos|ἄναρχος|ref}}.&lt;/ref&gt; from the [[privative]] prefix [[privative alpha|ἀν]]- (''an-'', i.e. &quot;without&quot;) and {{lang|grc|ἀρχός}}, ''archos'', i.e. &quot;leader&quot;, &quot;ruler&quot;;&lt;ref&gt;{{LSJ|a)rxo/s|ἀρχός|ref}}&lt;/ref&gt; (cf. ''[[ar:
"""
    txt2 = parse(txt)
    print txt2
