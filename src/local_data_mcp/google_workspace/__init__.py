"""Google Workspace integration (authentication, and later Sheets/Docs adapters).

Named ``google_workspace`` rather than ``google`` on purpose: a module named
``google`` would shadow the real ``google`` namespace used by Google's own
libraries (``import google.auth``) and break imports everywhere.
"""
