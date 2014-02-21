"""
Class for manipulating a syntax tree represented in RDF
"""
import re
from collections import namedtuple, defaultdict
from itertools import chain
import logging
import json

import requests
from unidecode import unidecode
from rdflib import ConjunctiveGraph, Namespace, Literal
from pygraphviz import AGraph

from .soh import SOHServer

log = logging.getLogger(__name__)

BASE = "http://example.com/jitp/"
NS_BASE = Namespace(BASE)
VIS_IGNORE_PROPERTIES = "id", "offset", "sentence", "uri", "word"
VIS_GREY_REL = lambda triple: ({'color': 'grey'}
                               if 'rel_' in triple.predicate else {})
RDF_TYPE = "http://www.w3.org/1999/02/22-rdf-syntax-ns#type"
Triple = namedtuple("Triple", ["subject", "predicate", "object"])


class Node(object):
    """
    Flexible 'record-like' object with arbitrary attributes for tokens
    """
    def __unicode__(self):
        return "Node(%s)" % ", ".join("%s=%r" % kv
                                      for kv in self.__dict__.iteritems())

    def __init__(self, **kargs):
        self.__dict__.update(kargs)
    __repr__ = __unicode__


class SyntaxTree(object):

    def __init__(self, soh):
        """
        @param soh: a SOH server object or url
        """
        if isinstance(soh, (str, unicode)):
            # it's probably a URL
            soh = SOHServer(soh)
        self.soh = soh
        self.soh.prefixes[""] = BASE

    def load_sentence(self, rdf_triples):
        """
        Load the given triples into the triple store
        """
        g = ConjunctiveGraph()
        g.bind("base", BASE)
        for triple in rdf_triples:
            g.add(triple)
        self.soh.add_triples(g, clear=True)

    def load_saf(self, saf_article, sentence_id):
        """
        Load triples from a SAF article
        (see https://github.com/anonymous-1/syntaxrules/blob/master/saf.md)
        @param saf_article: a dict, url, or file
        """
        if isinstance(saf_article, file):
            saf_article = json.load(file)
        elif isinstance(saf_article, (str, unicode)):
            saf_article = requests.get(saf_article).json()
        triples = _saf_to_rdf(saf_article, sentence_id)
        self.load_sentence(triples)

    def get_triples(self, ignore_rel=True, filter_predicate=None,
                    ignore_grammatical=False, minimal=False):
        """Retrieve the triples for the loaded sentence"""
        result = []
        if isinstance(filter_predicate, (str, unicode)):
            filter_predicate = [filter_predicate]
        nodes = {}
        for s, p, o in self.soh.get_triples():
            s = unicode(s)
            child = nodes.setdefault(s, Node(uri=s))

            pred = str(p).replace(BASE, "")
            if isinstance(o, Literal):
                if hasattr(child, pred):
                    o = getattr(child, pred) + "; " + o
                setattr(child, pred, unicode(o))
            else:
                o = unicode(o)
                if not ((ignore_rel and pred == "rel")
                        or (ignore_grammatical and pred.startswith("rel_"))
                        or (filter_predicate and pred not in filter_predicate)
                        or (pred == RDF_TYPE)):
                    parent = nodes.setdefault(o, Node(uri=o))
                    result.append(Triple(child, pred, parent))

        if minimal:
            return [{"subject": s.id,"predicate": p, "object": o.id}
                    for (s, p, o) in result]
        return result


    def apply_ruleset(self, ruleset):
        """
        Apply a set of rules to this tree.
        A ruleset should be a dict with rules and lexicon entries
        """
        self.apply_lexicon(ruleset['lexicon'])
        for rule in ruleset['rules']:
            self.apply_rule(rule)

    def apply_rule(self, rule):
        """
        Apply the given rule, which should be a dict with
        condition and insert and/or delete clauses
        """
        self.soh.update(where=rule['condition'],
                        insert=rule.get('insert', ''),
                        delete=rule.get('delete', ''))

    def get_tokens(self):
        tokens = defaultdict(dict)  # id : {attrs}
        for s, p, o in self.soh.get_triples():
            if isinstance(o, Literal):
                tokens[s][p.replace(NS_BASE, "")] = unicode(o)
        return tokens

    def apply_lexicon(self, lexicon):
        """
        Lexicon should consist of dicts with lexclass, lemma, and optional pos
        lemma can be a list or a string
        """
        for uri, token in self.get_tokens().iteritems():
            uri = str(uri).replace(BASE, ":")
            pos = token['pos']
            lemma = token['lemma'].lower()
            for lex in lexicon:
                if "pos" in lex and lex['pos'] != pos:
                    continue
                lemmata = lex['lemma']
                lexclass = lex['lexclass']
                if not isinstance(lemmata, list):
                    lemmata = [lemmata]
                for target in lemmata:
                    if target == lemma or (target.endswith("*")
                                           and lemma.startswith(target[:-1])):
                        insert = ('{uri} :lexclass "{lexclass}"'
                                  .format(**locals()))
                        self.soh.update(insert=insert)

    def get_graphviz(self, triple_args_function=None,
                     ignore_properties=VIS_IGNORE_PROPERTIES):
        """
        Create a pygraphviz graph from the tree
        """
        def _id(node):
            return node.uri.split("/")[-1]
        g = AGraph(directed=True)
        triples = list(self.get_triples())
        nodeset = set(chain.from_iterable((t.subject, t.object)
                                          for t in triples))
        for n in nodeset:
            label = "%s: %s" % (n.id, n.word)
            for k, v in n.__dict__.iteritems():
                if k not in ignore_properties:
                    label += "\\n%s: %s" % (k, v)
            g.add_node(_id(n), label=label)

        # create edges
        for triple in triples:
            kargs = (triple_args_function(triple)
                     if triple_args_function else {})
            if 'label' not in kargs:
                kargs['label'] = triple.predicate
            g.add_edge(_id(triple.subject), _id(triple.object), **kargs)
        # some theme options
        g.graph_attr["rankdir"] = "BT"
        g.node_attr["shape"] = "rect"
        g.edge_attr["edgesize"] = 10
        g.node_attr["fontsize"] = 10
        g.edge_attr["fontsize"] = 10

        return g


def _saf_to_rdf(saf_article, sentence_id):
    """
    Get the raw RDF subject, predicate, object triples
    representing the given analysed sentence
    """
    def _token_uri(token):
        lemma = unidecode(unicode(token['lemma']))
        uri = "t_{id}_{lemma}".format(id=token['id'], lemma=lemma)
        return NS_BASE[uri]

    def _rel_uri(dependency):
        return NS_BASE["rel_{rel}".format(rel=dependency['relation'])]

    tokens = {}  # token_id : uri
    for token in saf_article['tokens']:
        if int(token['sentence']) == sentence_id:
            uri = _token_uri(token)
            for k, v in token.iteritems():
                yield uri, NS_BASE[k], Literal(unidecode(unicode(v)))
            tokens[int(token['id'])] = uri

    for dep in saf_article['dependencies']:
        if int(dep['child']) in tokens:
            child = tokens[int(dep['child'])]
            parent = tokens[int(dep['parent'])]
            for pred in _rel_uri(dep), NS_BASE["rel"]:
                yield child, pred, parent
