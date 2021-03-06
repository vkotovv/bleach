import html5lib
import pytest
import six

import bleach


def test_empty():
    assert bleach.clean('') == ''


def test_nbsp():
    if six.PY3:
        expected = '\xa0test string\xa0'
    else:
        expected = six.u('\\xa0test string\\xa0')

    assert bleach.clean('&nbsp;test string&nbsp;') == expected


def test_comments_only():
    comment = '<!-- this is a comment -->'
    open_comment = '<!-- this is an open comment'
    assert bleach.clean(comment) == ''
    assert bleach.clean(open_comment) == ''
    assert bleach.clean(comment, strip_comments=False) == comment
    assert (
        bleach.clean(open_comment, strip_comments=False) ==
        '{0!s}-->'.format(open_comment)
    )


def test_with_comments():
    html = '<!-- comment -->Just text'
    assert 'Just text', bleach.clean(html) == 'Just text'
    assert bleach.clean(html, strip_comments=False) == html


def test_no_html():
    assert bleach.clean('no html string') == 'no html string'


def test_allowed_html():
    assert (
        bleach.clean('an <strong>allowed</strong> tag') ==
        'an <strong>allowed</strong> tag'
    )
    assert (
        bleach.clean('another <em>good</em> tag') ==
        'another <em>good</em> tag'
    )


def test_bad_html():
    assert (
        bleach.clean('a <em>fixed tag') ==
        'a <em>fixed tag</em>'
    )


def test_function_arguments():
    TAGS = ['span', 'br']
    ATTRS = {'span': ['style']}

    assert (
        bleach.clean('a <br/><span style="color:red">test</span>',
                     tags=TAGS, attributes=ATTRS) ==
        'a <br><span style="">test</span>'
    )


def test_named_arguments():
    ATTRS = {'a': ['rel', 'href']}

    text = '<a href="http://xx.com" rel="alternate">xx.com</a>'

    assert bleach.clean(text) == '<a href="http://xx.com">xx.com</a>'
    assert (
        bleach.clean(text, attributes=ATTRS) ==
        '<a href="http://xx.com" rel="alternate">xx.com</a>'
    )


def test_disallowed_html():
    assert (
        bleach.clean('a <script>safe()</script> test') ==
        'a &lt;script&gt;safe()&lt;/script&gt; test'
    )
    assert (
        bleach.clean('a <style>body{}</style> test') ==
        'a &lt;style&gt;body{}&lt;/style&gt; test'
    )


def test_bad_href():
    assert (
        bleach.clean('<em href="fail">no link</em>') ==
        '<em>no link</em>'
    )


def test_bare_entities():
    assert (
        bleach.clean('an & entity') ==
        'an &amp; entity'
    )
    assert (
        bleach.clean('an < entity') ==
        'an &lt; entity'
    )

    assert (
        bleach.clean('tag < <em>and</em> entity') ==
        'tag &lt; <em>and</em> entity'
    )

    assert (
        bleach.clean('&amp;') ==
        '&amp;'
    )


def test_escaped_entities():
    s = '&lt;em&gt;strong&lt;/em&gt;'
    assert bleach.clean(s) == s


def test_serializer():
    s = '<table></table>'
    assert bleach.clean(s, tags=['table']) == s
    assert bleach.linkify('<table>test</table>') == 'test<table></table>'
    assert bleach.clean('<p>test</p>', tags=['p']) == '<p>test</p>'


def test_no_href_links():
    s = '<a name="anchor">x</a>'
    assert bleach.linkify(s) == s


def test_weird_strings():
    s = '</3'
    assert bleach.clean(s) == ''


def test_xml_render():
    parser = html5lib.HTMLParser()
    assert bleach._render(parser.parseFragment('')) == ''


def test_stripping():
    assert (
        bleach.clean('a test <em>with</em> <b>html</b> tags', strip=True) ==
        'a test <em>with</em> <b>html</b> tags'
    )
    assert (
        bleach.clean('a test <em>with</em> <img src="http://example.com/"> <b>html</b> tags', strip=True) ==
        'a test <em>with</em>  <b>html</b> tags'
    )

    s = '<p><a href="http://example.com/">link text</a></p>'
    assert (
        bleach.clean(s, tags=['p'], strip=True) ==
        '<p>link text</p>'
    )
    s = '<p><span>multiply <span>nested <span>text</span></span></span></p>'
    assert (
        bleach.clean(s, tags=['p'], strip=True) ==
        '<p>multiply nested text</p>'
    )

    s = ('<p><a href="http://example.com/"><img src="http://example.com/">'
         '</a></p>')
    assert (
        bleach.clean(s, tags=['p', 'a'], strip=True) ==
        '<p><a href="http://example.com/"></a></p>'
    )


def test_allowed_styles():
    ATTR = ['style']
    STYLE = ['color']
    blank = '<b style=""></b>'
    s = '<b style="color: blue;"></b>'
    assert bleach.clean('<b style="top:0"></b>', attributes=ATTR) == blank
    assert bleach.clean(s, attributes=ATTR, styles=STYLE) == s
    assert (
        bleach.clean('<b style="top: 0; color: blue;"></b>', attributes=ATTR, styles=STYLE) ==
        s
    )


def test_idempotent():
    """Make sure that applying the filter twice doesn't change anything."""
    dirty = '<span>invalid & </span> < extra http://link.com<em>'

    clean = bleach.clean(dirty)
    assert bleach.clean(clean) == clean

    linked = bleach.linkify(dirty)
    assert (
        bleach.linkify(linked) ==
        '<span>invalid &amp; </span> &lt; extra <a href="http://link.com" rel="nofollow">http://link.com</a><em></em>'
    )


def test_rel_already_there():
    """Make sure rel attribute is updated not replaced"""
    linked = ('Click <a href="http://example.com" rel="tooltip">'
              'here</a>.')

    link_good = 'Click <a href="http://example.com" rel="tooltip nofollow">here</a>.'

    assert bleach.linkify(linked) == link_good
    assert bleach.linkify(link_good) == link_good


def test_lowercase_html():
    """We should output lowercase HTML."""
    dirty = '<EM CLASS="FOO">BAR</EM>'
    clean = '<em class="FOO">BAR</em>'
    assert bleach.clean(dirty, attributes=['class']) == clean


def test_wildcard_attributes():
    ATTR = {
        '*': ['id'],
        'img': ['src'],
    }
    TAG = ['img', 'em']
    dirty = ('both <em id="foo" style="color: black">can</em> have '
             '<img id="bar" src="foo"/>')
    assert (
        bleach.clean(dirty, tags=TAG, attributes=ATTR) ==
        'both <em id="foo">can</em> have <img id="bar" src="foo">'
    )


def test_callable_attributes():
    """Verify callable attributes work and get correct arg values"""
    def img_test(attr, val):
        return attr == 'src' and val.startswith('https')

    ATTR = {
        'img': img_test,
    }
    TAGS = ['img']

    assert (
        bleach.clean('foo <img src="http://example.com" alt="blah"> baz', tags=TAGS, attributes=ATTR) ==
        u'foo <img> baz'
    )
    assert (
        bleach.clean('foo <img src="https://example.com" alt="blah"> baz', tags=TAGS, attributes=ATTR) ==
        u'foo <img src="https://example.com"> baz'
    )


def test_svg_attr_val_allows_ref():
    """Unescape values in svg attrs that allow url references"""
    # Local IRI, so keep it
    text = '<svg><rect fill="url(#foo)" /></svg>'
    TAGS = ['svg', 'rect']
    ATTRS = {
        'rect': ['fill'],
    }
    assert (
        bleach.clean(text, tags=TAGS, attributes=ATTRS) ==
        '<svg><rect fill="url(#foo)"></rect></svg>'
    )

    # Non-local IRI, so drop it
    text = '<svg><rect fill="url(http://example.com#foo)" /></svg>'
    TAGS = ['svg', 'rect']
    ATTRS = {
        'rect': ['fill'],
    }
    assert (
        bleach.clean(text, tags=TAGS, attributes=ATTRS) ==
        '<svg><rect></rect></svg>'
    )


@pytest.mark.parametrize('text, expected', [
    (
        '<svg><pattern id="patt1" href="#patt2"></pattern></svg>',
        '<svg><pattern href="#patt2" id="patt1"></pattern></svg>'
    ),
    (
        '<svg><pattern id="patt1" xlink:href="#patt2"></pattern></svg>',
        # NOTE(willkg): Bug in html5lib serializer drops the xlink part
        '<svg><pattern id="patt1" href="#patt2"></pattern></svg>'
    ),
])
def test_svg_allow_local_href(text, expected):
    """Keep local hrefs for svg elements"""
    TAGS = ['svg', 'pattern']
    ATTRS = {
        'pattern': ['id', 'href'],
    }
    assert bleach.clean(text, tags=TAGS, attributes=ATTRS) == expected


@pytest.mark.parametrize('text, expected', [
    (
        '<svg><pattern id="patt1" href="https://example.com/patt"></pattern></svg>',
        '<svg><pattern id="patt1"></pattern></svg>'
    ),
    (
        '<svg><pattern id="patt1" xlink:href="https://example.com/patt"></pattern></svg>',
        '<svg><pattern id="patt1"></pattern></svg>'
    ),
])
def test_svg_allow_local_href_nonlocal(text, expected):
    """Drop non-local hrefs for svg elements"""
    TAGS = ['svg', 'pattern']
    ATTRS = {
        'pattern': ['id', 'href'],
    }
    assert bleach.clean(text, tags=TAGS, attributes=ATTRS) == expected




@pytest.mark.xfail(reason='html5lib >= 0.99999999: changed API')
def test_sarcasm():
    """Jokes should crash.<sarcasm/>"""
    dirty = 'Yeah right <sarcasm/>'
    clean = 'Yeah right &lt;sarcasm/&gt;'
    assert bleach.clean(dirty) == clean


def test_user_defined_protocols_valid():
    valid_href = '<a href="myprotocol://more_text">allowed href</a>'
    assert bleach.clean(valid_href, protocols=['myprotocol']) == valid_href


def test_user_defined_protocols_invalid():
    invalid_href = '<a href="http://xx.com">invalid href</a>'
    cleaned_href = '<a>invalid href</a>'
    assert bleach.clean(invalid_href, protocols=['my_protocol']) == cleaned_href
