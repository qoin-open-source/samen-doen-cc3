from django import template
from django.utils.http import urlencode

register = template.Library()


def var(variable, ctx):
    if variable:
        try:
            return template.Variable(variable).resolve(ctx)
        except template.VariableDoesNotExist:
            return None
    else:
        return None


def full_address_fn(ctx, street, city, number=None, country=None):
    street = var(street, ctx)
    city = var(city, ctx)
    number = var(number, ctx)
    country = var(country, ctx)

    if number:
        number += " "
    else:
        number = ""

    if not country:
        country = 'France'

    return street, city, number, country


@register.tag(name='full_address')
def full_address(parser, tokens):
    """
    Returns the address of the user in a form suitable for Google Maps:

    {% full_address street city num_street country %}
    """

    def render(ctx):
        (street, city, number, country) = full_address_fn(
            ctx, *(tokens.contents.split()[1:]))

        return "{0} {1}, {2}, {3}".format(number, street, city, country)

    res = template.Node()
    setattr(res, 'render', render)
    return res


@register.tag(name='static_map')
def static_map(parser, tokens):

    def render(ctx):
        (street, city, number, country) = full_address_fn(
            ctx, *(tokens.contents.split()[1:]))
        return static_map_fn(ctx, street, city, number, country)

    res = template.Node()
    setattr(res, 'render', render)
    return res


@register.tag(name='static_map_profile')
def static_map_profile(parser, tokens):
    """
    Displays a static map for a CC3Profile object:

    {% static_map_profile cc3_profile %}
    """

    def render(ctx):

        args = tokens.contents.split()
        if len(args) < 2:
            return ""

        cc3_profile = var(args[1], ctx)

        if cc3_profile:
            if cc3_profile.latitude and cc3_profile.longitude:

                loc = "{0},{1}".format(
                    cc3_profile.latitude,
                    cc3_profile.longitude)

                return render_static_map(loc, "color:red|"+loc)

            else:
                return static_map_fn(
                    ctx,
                    cc3_profile.street,
                    cc3_profile.city,
                    cc3_profile.num_street,
                    cc3_profile.country.name)

    res = template.Node()
    setattr(res, 'render', render)
    return res


def static_map_fn(ctx, street, city, number=None,
                  country=None, w=275, h=275):

    if not street or not city or not country:
        return ""
    else:
        return render_static_map(
            "{0} {1}, {2}, {3}".format(number, street, city, country),
            "color:red|{0} {1}, {2}, {3}".format(
                number, street, city, country),
            w, h)


def render_static_map(center, markers, w=300, h=300):

    url = '<a target="_blank" href="http://maps.google.com/maps?{0}">{1}</a>'

    img = (
        u'<img src="http://maps.googleapis.com/maps/api/staticmap?'
        u'{0}&zoom=15'
        u'&maptype=roadmap96&sensor=false">')

    image = img.format(
        urlencode({
            'center': center,
            'markers': markers,
            'size': "{0}x{1}".format(w, h)
        }))

    return url.format(
        urlencode({'q': center}),
        image)
