Using Grammatical Analysis to Study Framing
===========================================

This is an anonymous repository containing the source code developed for
an article under review. The source code will be published in a 'normal'
repository in case the article is accepted.

Package to apply transformation rules to (syntax) graphs.

Installing
----------

(tested on Ubuntu linux 13.10)

This package depends on pygraphviz, which requires the development libraries
for python and graphviz. On debian/ubuntu, use the following command (which
will also install git, if needed):

    sudo apt-get git install libgraphviz-dev python-dev

Then, install directly from github using pip:

    sudo pip install git+https://github.com/anonymous-1/syntaxrules


Sparql
------

SyntaxRules requires a SPARQL 1.1 server to be available over HTTP, which
supports /data (PUT, POST, GET) and /query and /update (POST). One option
is using fuseki, which can be downloaded from
http://jena.apache.org/documentation/serving_data/
I used the following commands to get fuseki running:

```bash
get http://repository.apache.org/content/repositories/snapshots/org/apache/jena/jena-fuseki/1.0.2-SNAPSHOT/jena-fuseki-1.0.2-20140219.080217-28-distribution.tar.gz
tar -xvzf jena-fuseki-1.0.2-20140219.080217-28-distribution.tar.gz
cd jena-fuseki-1.0.2-SNAPSHOT/
./fuseki-server --update --mem --port 3030 /x
```


Note: I've not tested with any other SPARQL servers than fuseki, so please
create an issue or pull request if adaptation is needed for other servers.


Usage
-----

The main interface is the syntaxrules.syntaxtree.SyntaxTree class. The following
code creates a SyntaxTree object pointing to the fuseki server started above:

```python
from syntaxrules import SyntaxTree
t = SyntaxTree("http://localhost:3030/x")
```

A parsed sentence can be loaded into the SyntaxTree from a url, file, or (json) dict.
This code loads the first sentence from the
[article in the unit tests](https://github.com/anonymous-1/syntaxrules/blob/master/tests/test_saf.json):
(see below for format specifications)

```python
import requests
saf_url = "https://raw.github.com/anonymous-1/syntaxrules/master/tests/test_saf.json"
saf = requests.get(saf_url).json()
t.load_saf(saf, sentence_id=1)
```

This tree can be visualized using graphviz:

```python
t.get_graphviz().draw("/tmp/test.png", prog="dot")
```

Rulesets contain a lexicon and transformation rules that can add or remove relations to/from
the graph. This code loads
[the ruleset from the tests](https://github.com/anonymous-1/syntaxrules/blob/master/tests/test_rules.json)
and applies it to the loaded sentence:

```python
ruleset_url = "https://raw.github.com/anonymous-1/syntaxrules/master/tests/test_rules.json"
ruleset = requests.get(ruleset_url).json()
t.apply_ruleset(ruleset)
```

The triples can then be retrieved from the tree as python namedtuple objects (ignore_grammatical=True
means that the original grammatical relations are not returned):

```python
triples = t.get_triples(ignore_grammatical=True)
print(triples[0].subject)
```

> Node(lexclass=u'person', word=u'John', sentence=u'1', pos=u'NNP', uri=u'http://example.com/jitp/t_1_John', lemma=u'John', offset=u'0', id=u'1')

And they can also be extracted as a json-ready minimal dict, refering to the
ids from the original tokens layer:

```python
print t.get_triples(ignore_grammatical=True, minimal=True)
```

> [{"predicate": "marry", "object": "3", "subject": "1"}]


The result can also be visualized again, using a callback function to make the original syntactic
relations grey so the new relation stands out:

```python
from syntaxrules import VIS_GREY_REL
t.get_graphviz().draw("/tmp/test.png", prog="dot")
g = t.get_graphviz(triple_args_function=VIS_GREY_REL)
g.draw("/tmp/test2.png", prog="dot")
```

Representation Formats
----------------------

The articles are accepted in 'SAF', which is a layer-based json format that is very similar to the
newsreader annotation format (NAF). Note that this format is under development and subject to change.
See https://gist.github.com/anonymous-1/9027118

Feel free to open an issue or pull request to provide support for additional formats.

The rulesets are accepted in a simple json format. A ruleset consists of a 'lexicon' and a list of 'rules'.

The lexicon is a list of entries, which are dictionaries with lexclass, lemma, and optional pos filter.
Any node with a lemma in the lemma list and optionally the correct pos will be tagged with the lexclass.

The rules are dictionaries containing a condition and insert and/or remove, all giving as SPARQL clauses.


    {"lexicon" : [
        {"lexclass": "desire", "lemma": ["want", "wish*", "desire"]}
        ],
     "rules" : [
        {"condition": "...", "insert": "..."}
        {"condition": "...", "remove": "..."}
        ]
    }
