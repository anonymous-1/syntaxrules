import logging
import json
import sys
import os.path
import tempfile

from nose.tools import assert_equal, assert_false, assert_in
from unittest import SkipTest

from syntaxrules.soh import SOHServer
from syntaxrules.syntaxtree import SyntaxTree, VIS_GREY_REL, NS_BASE, BASE

import syntaxrules
_ROOT = os.path.dirname(syntaxrules.__file__)
TEST_SAF = json.load(open(os.path.join(_ROOT, "../tests/test_saf.json")))
TEST_RULES = json.load(open(os.path.join(_ROOT, "../tests/test_rules.json")))


def test_saf_to_rdf():
    from syntaxrules.syntaxtree import _saf_to_rdf

    triples = set(tuple(str(x).replace(BASE, ":")
                        for x in spo)
                  for spo in _saf_to_rdf(TEST_SAF, sentence_id=1))

    from_john = set((p, o) for (s, p, o) in triples
                    if s == ':t_1_John')
    assert_equal(from_john, {(':sentence', '1'),
                             (':word', 'John'),
                             (':offset', '0'),
                             (':pos', 'NNP'),
                             (':id', '1'),
                             (':lemma', 'John'),
                             (':rel_nsubj', ':t_2_marry'),
                             (':rel', ':t_2_marry'),
                             })

    subjects = set(s for (s, p, o) in triples)
    assert_equal(subjects, {':t_1_John', ':t_2_marry', ':t_3_Mary'})

    triples = set(tuple(str(x).replace(BASE, ":")
                        for x in spo)
                  for spo in _saf_to_rdf(TEST_SAF, sentence_id=2))

    subjects = set(s for (s, p, o) in triples)
    assert_equal(subjects, {':t_4_it', ':t_5_rain'})
    relations = set((s, p, o) for (s, p, o) in triples if o.startswith(":"))
    assert_equal(relations, {(':t_4_it', ':rel', ':t_5_rain'),
                             (':t_4_it', ':rel_nsubj', ':t_5_rain')})


def _check_soh():
    import socket
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        result = s.connect(('127.0.0.1', 3030))
    except:
        logging.exception("Could not connect to SOH server")
        raise SkipTest("Could not connect to SOH Server at 127.0.0.1:3300, "
                       "skipping test")


def _get_tree(sid=1):
    _check_soh()
    soh = SOHServer(url="http://localhost:3030/x")
    t = SyntaxTree(soh)
    t.load_saf(TEST_SAF, sid)
    return t


def test_load():
    t = _get_tree(sid=2)
    triples = list(t.get_triples())
    assert_equal(len(triples), 1)
    assert_equal(triples[0].predicate, 'rel_nsubj')
    assert_equal(triples[0].subject.lemma, 'it')
    assert_equal(triples[0].object.lemma, 'rain')


def test_lexicon():
    t = _get_tree()
    t.apply_lexicon(TEST_RULES['lexicon'])

    classes = {k.replace(NS_BASE, ":"): str(v.get('lexclass'))
               for (k, v) in t.get_tokens().iteritems()}
    assert_equal(classes, {":t_2_marry": "marry",
                           ":t_3_Mary": 'person',
                           ':t_1_John': 'person'})


def test_rules():
    t = _get_tree()
    t.apply_ruleset(TEST_RULES)
    triples = [tr for tr in t.get_triples() if tr.predicate == "marry"]

    assert_equal(len(triples), 1)
    assert_equal(triples[0].subject.lemma, 'John')
    assert_equal(triples[0].object.lemma, 'Mary')


def test_graph():
    t = _get_tree()
    g = t.get_graphviz()
    assert_equal(set(g.edges()), {(u't_3_Mary', u't_2_marry'),
                                  (u't_1_John', u't_2_marry')})
    assert_in("lemma: John", g.get_node("t_1_John").attr["label"])

    # Can we 'gray out' syntax relations after applying rules
    t.apply_ruleset(TEST_RULES)
    t.apply_lexicon([{"lexclass": "man", "lemma": "john"}])
    g = t.get_graphviz(triple_args_function=VIS_GREY_REL)
    assert_equal(set(g.edges()), {(u't_3_Mary', u't_2_marry'),
                                  (u't_1_John', u't_2_marry'),
                                  (u't_1_John', u't_3_Mary')})
    assert_false(g.get_edge(u't_1_John', u't_3_Mary').attr.get("color"))
    assert_equal(g.get_edge(u't_1_John', u't_2_marry').attr.get("color"),
                 "grey")

    # can we draw it? can't check output, but we can check for errors
    with tempfile.NamedTemporaryFile() as f:
        g.draw(f.name, prog="dot")
        g.draw("/tmp/test.png", prog="dot")
