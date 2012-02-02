"""Worry-free YAML configuration files.
"""

class ConfigError(Exception):
    """Base class for exceptions raised when querying a configuration.
    """
    pass
class NotFoundError(ConfigError):
    """A requested value could not be found in the configuration trees.
    """
    pass
class ConfigTypeError(ConfigError, TypeError):
    """The value in the configuration did not match the expected type.
    """
    pass

class ConfigView(object):
    """A configuration "view" is a query into a program's configuration
    data. A view represents a hypothetical location in the configuration
    tree; to extract the data from the location, a client typically
    calls the ``view.get()`` method. The client can access children in
    the tree (subviews) by subscripting the parent view (i.e.,
    ``view[key]``).
    """
    def get_all(self):
        """Generates all available values for the view in the order of
        the configuration's sources. (Each source may have at most one
        value for each view.) If no values are available, no values are
        generated. If a type error is encountered when traversing a
        source to resolve the view, a ConfigTypeError may be raised.
        """
        raise NotImplementedError

    def get(self, typ=None):
        """Returns the canonical value for the view. This amounts to the
        first item in ``view.get_all()``. If the view cannot be
        resolved, this method raises a NotFoundError.
        """
        values = self.get_all()

        # Get the first value.
        try:
            value = iter(values).next()
        except StopIteration:
            raise NotFoundError(u"%s not found" % self.name())

        # Check the type.
        if typ is not None and not isinstance(value, typ):
            raise ConfigTypeError(u"%s must by of type %s, not %s" %
                                  (self.name(), unicode(typ),
                                  unicode(type(value))))

        return value

    def name(self):
        """Returns the name of the view, depicting the path taken
        through the configuration in Python-like syntax (e.g.,
        ``foo['bar'][42]``).
        """
        raise NotImplementedError

    def __repr__(self):
        return '<ConfigView: %s>' % self.name()

    def __getitem__(self, key):
        """Get a subview of this view."""
        return Subview(self, key)

    # Magical conversions. These special methods make it possible to use
    # View objects somewhat transparently in certain circumstances. For
    # example, rather than using ``view.get(bool)``, it's possible to
    # just say ``bool(view)`` or use ``view`` in a conditional.

    def __str__(self):
        """Gets the value for this view as a byte string."""
        return str(self.get())
    
    def __unicode__(self):
        """Gets the value for this view as a unicode string."""
        return unicode(self.get())
    
    def __nonzero__(self):
        """Gets the value for this view as a boolean."""
        return bool(self.get())

    # Dictionary emulation methods.

    def keys(self):
        """Returns an iterable containing all the keys available as
        subviews of the current views. This enumerates all the keys in
        *all* dictionaries matching the current view, in contrast to
        ``dict(view).keys()``, which gets all the keys for the *first*
        dict matching the view. If the object for this view in any
        source is not a dict, then a ConfigTypeError is raised.
        """
        keys = set()
        for dic in self.get_all():
            try:
                keyit = dic.iterkeys()
            except AttributeError:
                raise ConfigTypeError(u'%s must be a dict, not %s' %
                                      (self.name(), unicode(type(dic))))
            keys.update(keyit)
        return keys

    def items(self):
        """Iterates over (key, subview) pairs contained in dictionaries
        from *all* sources at this view. If the object for this view in
        any source is not a dict, then a ConfigTypeError is raised.
        """
        for key in self.keys():
            yield key, self[key]

    def values(self):
        """Iterates over all the subviews contained in dictionaries from
        *all* sources at this view. If the object for this view in any
        source is not a dict, then a ConfigTypeError is raised.
        """
        for key in self.keys():
            yield self[key]

    # List/sequence emulation.

    def all_contents(self):
        """Iterates over all subviews from collections at this view from
        *all* sources. If the object for this view in any source is not
        iterable, then a ConfigTypeError is raised. This method is
        intended to be used when the view indicates a list; this method
        will concatenate the contents of the list from all sources.
        """
        for collection in self.get_all():
            try:
                it = iter(collection)
            except TypeError:
                raise ConfigTypeError(u'%s must be an iterable, not %s' %
                                      (self.name(), unicode(type(collection))))
            for value in it:
                yield value

class RootView(ConfigView):
    """The base of a view hierarchy. This view keeps track of the
    sources that may be accessed by subviews.
    """
    def __init__(self, sources):
        """Create a configuration hierarchy for a list of sources. At
        least one source must be provided. The first source in the list
        has the highest priority.
        """
        if not sources:
            raise ValueError('no sources supplied')
        self.sources = sources

    def get_all(self):
        return self.sources

    def name(self):
        return u"root"

class Subview(ConfigView):
    """A subview accessed via a subscript of a parent view."""
    def __init__(self, parent, key):
        """Make a subview of a parent view for a given subscript key.
        """
        self.parent = parent
        self.key = key

    def get_all(self):
        for collection in self.parent.get_all():
            try:
                value = collection[self.key]
            except IndexError:
                # List index out of bounds.
                continue
            except KeyError:
                # Dict key does not exist.
                continue
            except TypeError:
                # Not subscriptable.
                raise ConfigTypeError(u"%s must be a collection, not %s" %
                                      (self.parent.name(),
                                       unicode(type(collection))))
            yield value

    def name(self):
        return u"%s[%s]" % (self.parent.name(), repr(self.key))
