Copied the sphinx_rtd_theme layout.html (found in
[ENVIRONMENT PATH]/lib/python3.9/site-packages/sphinx_rtd_theme/layout.html
) to _templates/ and added the following line:

```
<script type="text/javascript" id="documentation_options" data-url_root="{{ pathto('', 1) }}" src="{{ pathto('_static/documentation_options.js', 1) }}"></script>
```

Above the import of documentation_options.js to fix search (prevent a `Stemmer
is no defined` JS error).

When updating the RTD theme, recopy the layout.html and re-add the import.

See related:

    * StackOverflow: https://stackoverflow.com/questions/52474177/read-the-docs-search-broken
    * GitHub: https://github.com/sphinx-doc/sphinx/issues/5460
    * Example Fix: https://github.com/HangfireIO/Hangfire.Documentation/commit/de122cc40a3df6c387bd9b6bff0aa6d14ab66f80
