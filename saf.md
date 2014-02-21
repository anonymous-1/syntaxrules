A simple annotation format
==========================

Annotation formats have a habit of changing with new technologies and frameworks. That said, there are a number of things that most people working in NLP can probably agree on. Codifying such agreement in a technical implementation makes it easier to collaborate on tools and infrastructure.

This document proposes a simple extensible json-based format that is intended to capture the part of NLP representation that we cal all agree on and that is simple to use, store, and extend. It does not force every tool or every user to adhere to this format. Rather, it is intended as a suggestion to developers that if the output of their module can fit in this format, it might be a good idea to use it, so we can all work together better.

General idea and motivating example
===================================

The format is layer based, with different levels of representation pointing to the previous level using ids. The basic unit is the token, and most layers refer directly to tokens, but this is not a requirement. Attributes on the unit give information such as word, lemma, relation, named entitiy type, et cetera.

The overall document structure is a json dict containing the layers, which each consist of a list of units represented as dicts. Apart from the layers, the document contains a header to specify file format and analyzers provenance.

For example, suppose we have a document containing the sentence “John wrote this!”, processed by a POS-tagger. The resulting document could be something like:

```json
{
"header" : {"format" : "SAF",
            "format-version" : "0.1",
            "processed" : [
                {"module" : "POSTagger",
                 "module-version": "1.2",
                 "started" : "2014-02-14",
                }
            ]
           },
"tokens" : [{"id" : 1, "sentence" : 1, "offset": 0, "word" : "John", "pos" : "M"},
	    {"id" : 2, "sentence" : 1, "offset": 6, "word" : "wrote", "pos" : "V"},
	    {"id" : 3, "sentence" : 1, "offset": 13, "word" : "wrote", "pos" : "O"},
            {"id" : 4, "sentence" : 1, "offset": 13, "word" : "wrote", "pos" : "V"}
           ]
}
```

If this sentence is then parsed, it could add a dependency layer like:

```json
{"dependencies" : [{"parent" : 2, "child" : 1, "relation": "su"},
		   {"parent" : 2, "child" : 3, "relation": "dobj"}]
}
```

This format specifies a number of layers and (optional and required) attributes. A complying document contains one or more of these layers and each of the required attributes for that layer. Optional attributes may be used but should be used as intended by the specification. Other layers and attributes may be added as desired.

Specification
=============

Header
------

The header is a dictionary with meta-information about the represented content. The header is optional and can be left out for performance reasons if desired. There are three attributes defined on the header, all required:

```
format: “SAF”, indicating that the document is formatted according to this standard.
format-version: the version of this document used for the representation
processed: a list of modules that have been used to process this document. Entries contain:
module: the name of the module, preferably a technical name that is sufficient for the system to rerun the analysis (e.g. python modulename.classname or celery task name)
module-version: the version of the module used
started: the timestamp at which the processing of this document was started
arguments: an optional list or dict of parameters passed to the processing module
```

Tokens
------

Tokens represent words/terms/tokens are generally output by many NLP processing tools.

```
id which is unique in this document
word: the word (more or less) as encountered in the text
sentence (optional): a number or id of the sentence.
offset (optional): the character position of the start of this token within the document or sentence. If sentence is given, this should point to the offset with the sentence
pos (optional): a unspecified representation of the part of speech tag
lemma (optional): the lemma (or stem) of the word
pos-confidence (optional): a decimal number in the range 0-1 indicating confidence in the POS tag
lemma-confidence (optional): a decimal number in the range 0-1 indicating confidence in the lemma
```

Dependencies
------------

```
parent: the token id of the parent node
child: the token id of the child node
relation: an (unspecified) representation of the relation between parent and child.
confidence (optional): a decimal number in the range 0-1 indicating confidence in this dependency
```
