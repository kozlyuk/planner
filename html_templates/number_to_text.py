import decimal


units = (
    u'нуль',

    (u'один', u'одна'),
    (u'два', u'дві'),

    u'три', u'чотири', u"п'ять",
    u'шість', u'сім', u'вісім', u"дев'ять"
)

teens = (
    u'десять', u'одинадцять',
    u'дванадцять', u'тринадцять',
    u'чотирнадцять', u"п'ятнадцять",
    u'шістнадцять', u'сімнадцять',
    u'вісімнадцять', u"дев'ятнадцять"
)

tens = (
    teens,
    u'двадцять', u'тридцять',
    u'сорок', u"п'ятдесят",
    u'шістдесят', u'сімдесят',
    u'вісімдесят', u"дев'яносто"
)

hundreds = (
    u'сто', u'двісті',
    u'триста', u'чотириста',
    u"п'ятсот", u'шістсот',
    u'сімсот', u'вісімсот',
    u"дев'ятсот"
)

orders = (# plural forms and gender
    # ((u'', u'', u''), 'm'),
    # ((u'рубль', u'рубля', u'рублей'), 'm'),
    # ((u'копейка', u'копейки', u'копеек'), 'f'),
    ((u'тисяча', u'тисячі', u'тисяч'), 'f'),
    ((u'мільйон', u'мильйона', u'мильйонів'), 'm'),
    ((u'мільярд', u'мільяарди', u'мільярдів'), 'm'),
)

minus = u'мінус'


def thousand(rest, sex):
    """Converts numbers from 19 to 999"""
    prev = 0
    plural = 2
    name = []
    use_teens = rest % 100 >= 10 and rest % 100 <= 19
    if not use_teens:
        data = ((units, 10), (tens, 100), (hundreds, 1000))
    else:
        data = ((teens, 10), (hundreds, 1000))
    for names, x in data:
        cur = int(((rest - prev) % x) * 10 / x)
        prev = rest % x
        if x == 10 and use_teens:
            plural = 2
            name.append(teens[cur])
        elif cur == 0:
            continue
        elif x == 10:
            name_ = names[cur]
            if isinstance(name_, tuple):
                name_ = name_[0 if sex == 'm' else 1]
            name.append(name_)
            if cur >= 2 and cur <= 4:
                plural = 1
            elif cur == 1:
                plural = 0
            else:
                plural = 2
        else:
            name.append(names[cur-1])
    return plural, name


def num2text(num, main_units=((u'', u'', u''), 'm')):
    """
    http://ru.wikipedia.org/wiki/Gettext#.D0.9C.D0.BD.D0.BE.D0.B6.D0.B5.D1.81.\
    D1.82.D0.B2.D0.B5.D0.BD.D0.BD.D1.8B.D0.B5_.D1.87.D0.B8.D1.81.D0.BB.D0.B0_2
    """
    _orders = (main_units,) + orders
    if num == 0:
        return ' '.join((units[0], _orders[0][0][2])).strip() # ноль

    rest = abs(num)
    ord = 0
    name = []
    while rest > 0:
        plural, nme = thousand(rest % 1000, _orders[ord][1])
        if nme or ord == 0:
            name.append(_orders[ord][0][plural])
        name += nme
        rest = int(rest / 1000)
        ord += 1
    if num < 0:
        name.append(minus)
    name.reverse()
    return ' '.join(name).strip()


def decimal2text(value, places=2,
                 int_units=(('', '', ''), 'm'),
                 exp_units=(('', '', ''), 'm')):
    value = decimal.Decimal(value)
    q = decimal.Decimal(10) ** -places

    integral, exp = str(value.quantize(q)).split('.')
    return u'{} {}'.format(
        num2text(int(integral), int_units),
        num2text(int(exp), exp_units))
