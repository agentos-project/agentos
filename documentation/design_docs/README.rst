===================
AgentOS Design Docs
===================

This folder holds design documents and proposals for AgentOS internals.


============
Contributing
============

If you'd like to contribute a design document or proposal, please:

* Start a new
  `Discussion <https://github.com/agentos-project/agentos/discussions>`_
  under the "Ideas" category.

* Iterate on the idea with community members via comments in that Discussion.

* When you have support by the committers, the discussion is migrated from the
  "Ideas" category to the "Designs" category by changing the category in the
  original discussion (or, if it makes more sense a new discussion can be
  created that references the original), and...

  * For smaller features, the body text of the discussion thread acts as the
    design doc, reviews happen via comments in the discussion thread and
    feedback is merged into the "doc" by editing the original discussion text
    (in this scenario, version history will not be captured).

  * For large designs, a document written in `reStructuredText
    <https://www.sphinx-doc.org/en/master/usage/restructuredtext/basics.html>`_
    may be created in this (the `design_docs`) folder. If it is owned by a
    committer, then they may edit it at will without using a fork or PRs. This
    keeps the design process lightweight while capturing revision history of the
    document. You might also find the `reStructuredText Quick Reference
    <https://docutils.sourceforge.io/docs/user/rst/quickref.html>`_ useful.


==================
Recommended Format
==================

Please include the following sections and items in your design document:

* **Abstract** - A brief paragraph summary of the design

* **Rationale** - The reason why this feature is important or useful

* **Demo** - A "demo" of what the feature will look like after implementation.
  This can contain pseudocode or command line examples.

* **Work items** - This is a set of items required to accomplish the proposed
  design.

* **FAQ** - Frequently asked questions.  Especially useful to address questions
  from your reviewer.

* **Open Questions** - A section to record things that should be investigated or
  may change as the design gets implemented.

* Links to any pull requests related to the document so comment history and
  debate can be discovered.
