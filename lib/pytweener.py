# pyTweener
#
# Tweening functions for python
#
# Heavily based on caurina Tweener: http://code.google.com/p/tweener/
#
# Released under M.I.T License - see above url
# Python version by Ben Harling 2009
# All kinds of slashing and dashing by Toms Baugis 2010
import math
import collections
import datetime as dt
import time
import re

class Tweener(object):
    def __init__(self, default_duration = None, tween = None):
        """Tweener
        This class manages all active tweens, and provides a factory for
        creating and spawning tween motions."""
        self.current_tweens = collections.defaultdict(set)
        self.default_easing = tween or Easing.Cubic.ease_in_out
        self.default_duration = default_duration or 1.0

    def has_tweens(self):
        return len(self.current_tweens) > 0


    def add_tween(self, obj, duration = None, easing = None, on_complete = None, on_update = None, **kwargs):
        """
            Add tween for the object to go from current values to set ones.
            Example: add_tween(sprite, x = 500, y = 200, duration = 0.4)
            This will move the sprite to coordinates (500, 200) in 0.4 seconds.
            For parameter "easing" you can use one of the pytweener.Easing
            functions, or specify your own.
            The tweener can handle numbers, dates and color strings in hex ("#ffffff")
        """
        if duration is None:
            duration = self.default_duration

        easing = easing or self.default_easing

        tw = Tween(obj, duration, easing, on_complete, on_update, **kwargs )

        if obj in self.current_tweens:
            for current_tween in self.current_tweens[obj]:
                prev_keys = set((tweenable.key for tweenable in current_tween.tweenables))
                dif = prev_keys & set(kwargs.keys())

                removable = [tweenable for tweenable in current_tween.tweenables if tweenable.key in dif]
                for tweenable in removable:
                    current_tween.tweenables.remove(tweenable)


        self.current_tweens[obj].add(tw)
        return tw


    def get_tweens(self, obj):
        """Get a list of all tweens acting on the specified object
        Useful for manipulating tweens on the fly"""
        return self.current_tweens.get(obj, None)

    def kill_tweens(self, obj = None):
        """Stop tweening an object, without completing the motion or firing the
        on_complete"""
        if obj:
            try:
                del self.current_tweens[obj]
            except:
                pass
        else:
            self.current_tweens = collections.defaultdict(set)

    def remove_tween(self, tween):
        """"remove given tween without completing the motion or firing the on_complete"""
        if tween.target in self.current_tweens and tween in self.current_tweens[tween.target]:
            self.current_tweens[tween.target].remove(tween)

    def finish(self):
        """jump the the last frame of all tweens"""
        for obj in self.current_tweens:
            for t in self.current_tweens[obj]:
                t._update(t.duration)
        self.current_tweens = {}

    def update(self, delta_seconds):
        """update tweeners. delta_seconds is time in seconds since last frame"""

        done_list = set()
        for obj in self.current_tweens:
            for tween in self.current_tweens[obj]:
                done = tween._update(delta_seconds)
                if done:
                    done_list.add(tween)

        # remove all the completed tweens
        for tween in done_list:
            if tween.on_complete:
                tween.on_complete(tween.target)

            self.current_tweens[tween.target].remove(tween)
            if not self.current_tweens[tween.target]:
                del self.current_tweens[tween.target]


class Tween(object):
    __slots__ = ('tweenables', 'target', 'delta', 'duration',
                 'ease', 'delta', 'on_complete',
                 'on_update', 'complete')

    def __init__(self, obj, duration, easing, on_complete, on_update, **kwargs):
        """Tween object use Tweener.add_tween( ... ) to create"""
        self.duration = duration
        self.target = obj
        self.ease = easing

        # list of (property, start_value, delta)
        self.tweenables = set()
        for key, value in kwargs.items():
            self.tweenables.add(Tweenable(key, self.target.__dict__[key], value))

        self.delta = 0
        self.on_complete = on_complete
        self.on_update = on_update
        self.complete = False

    def _update(self, ptime):
        """Update tween with the time since the last frame"""
        self.delta = self.delta + ptime
        if self.delta > self.duration:
            self.delta = self.duration

        if self.delta == self.duration:
            for tweenable in self.tweenables:
                self.target.__setattr__(tweenable.key, tweenable.target_value)
        else:
            fraction = self.ease(self.delta / self.duration)

            for tweenable in self.tweenables:
                self.target.__setattr__(tweenable.key, tweenable.update(fraction))

        if self.delta == self.duration or len(self.tweenables) == 0:
            self.complete = True

        if self.on_update:
            self.on_update(self.target)

        return self.complete




class Tweenable(object):
    hex_color_normal = re.compile("#([a-fA-F0-9]{2})([a-fA-F0-9]{2})([a-fA-F0-9]{2})")
    hex_color_short = re.compile("#([a-fA-F0-9])([a-fA-F0-9])([a-fA-F0-9])")

    def __init__(self, key, start_value, target_value):
        self.key = key
        self.change = None
        self.decode_func = lambda x: x
        self.encode_func = lambda x: x
        self.start_value = start_value
        self.target_value = target_value

        if isinstance(start_value, int) or isinstance(start_value, float):
            self.start_value = start_value
            self.change = target_value - start_value
        else:
            if isinstance(start_value, dt.datetime) or isinstance(start_value, dt.date):
                self.decode_func = lambda x: time.mktime(x.timetuple())
                if isinstance(start_value, dt.datetime):
                    self.encode_func = lambda x: dt.datetime.fromtimestamp(x)
                else:
                    self.encode_func = lambda x: dt.date.fromtimestamp(x)

                self.start_value = self.decode_func(start_value)
                self.change = self.decode_func(target_value) - self.start_value

            elif isinstance(start_value, basestring) \
             and (self.hex_color_normal.match(start_value) or self.hex_color_short.match(start_value)):
                # code below is mainly based on jquery-color plugin
                self.encode_func = lambda val: "#%02x%02x%02x" % (max(min(val[0], 255), 0),
                                                                  max(min(val[1], 255), 0),
                                                                  max(min(val[2], 255), 0))
                if self.hex_color_normal.match(start_value):
                    self.decode_func = lambda val: [int(match, 16)
                                                    for match in self.hex_color_normal.match(val).groups()]

                elif self.hex_color_short.match(start_value):
                    self.decode_func = lambda val: [int(match + match, 16)
                                                    for match in self.hex_color_short.match(val).groups()]

                if self.hex_color_normal.match(target_value):
                    target_value = [int(match, 16)
                                    for match in self.hex_color_normal.match(target_value).groups()]
                else:
                    target_value = [int(match + match, 16)
                                    for match in self.hex_color_short.match(target_value).groups()]

                self.start_value = self.decode_func(start_value)
                self.change = [target - start for start, target in zip(self.start_value, target_value)]


    def update(self, fraction):
        # list means we are dealing with a color triplet
        if isinstance(self.start_value, list):
            return self.encode_func([self.start_value[i] + self.change[i] * fraction for i in range(3)])
        else:
            return self.encode_func(self.start_value + self.change * fraction)



"""Robert Penner's classes stripped from the repetetive c,b,d mish-mash
(discovery of Patryk Zawadzki). This way we do the math once and apply to
all the tweenables instead of repeating it for each attribute
"""

def inverse(method):
    def real_inverse(t, *args, **kwargs):
        t = 1 - t
        return 1 - method(t, *args, **kwargs)
    return real_inverse

def symmetric(ease_in, ease_out):
    def real_symmetric(t, *args, **kwargs):
        if t < 0.5:
            return ease_in(t * 2, *args, **kwargs) / 2

        return ease_out((t - 0.5) * 2, *args, **kwargs) / 2 + 0.5
    return real_symmetric

class Symmetric(object):
    def __init__(self, ease_in = None, ease_out = None):
        self.ease_in = ease_in or inverse(ease_out)
        self.ease_out = ease_out or inverse(ease_in)
        self.ease_in_out = symmetric(self.ease_in, self.ease_out)


class Easing(object):
    """Class containing easing classes to use together with the tweener.
       All of the classes have :func:`ease_in`, :func:`ease_out` and
       :func:`ease_in_out` functions."""

    Linear = Symmetric(lambda t: t, lambda t: t)
    Quad = Symmetric(lambda t: t*t)
    Cubic = Symmetric(lambda t: t*t*t)
    Quart = Symmetric(lambda t: t*t*t*t)
    Quint = Symmetric(lambda t: t*t*t*t*t)
    Strong = Quint #oh i wonder why but the ported code is the same as in Quint

    Circ = Symmetric(lambda t: 1 - math.sqrt(1 - t * t))
    Sine = Symmetric(lambda t: 1 - math.cos(t * (math.pi / 2)))


    def _back_in(t, s=1.70158):
        return t * t * ((s + 1) * t - s)
    Back = Symmetric(_back_in)


    def _bounce_out(t):
        if t < 1 / 2.75:
            return 7.5625 * t * t
        elif t < 2 / 2.75:
            t = t - 1.5 / 2.75
            return 7.5625 * t * t + 0.75
        elif t < 2.5 / 2.75:
            t = t - 2.25 / 2.75
            return 7.5625 * t * t + .9375
        else:
            t = t - 2.625 / 2.75
            return 7.5625 * t * t + 0.984375
    Bounce = Symmetric(ease_out = _bounce_out)


    def _elastic_in(t, springiness = 0, wave_length = 0):
        if t in(0, 1):
            return t

        wave_length = wave_length or (1 - t) * 0.3

        if springiness <= 1:
            springiness = t
            s = wave_length / 4
        else:
            s = wave_length / (2 * math.pi) * math.asin(t / springiness)

        t = t - 1
        return -(springiness * math.pow(2, 10 * t) * math.sin((t * t - s) * (2 * math.pi) / wave_length))
    Elastic = Symmetric(_elastic_in)


    def _expo_in(t):
        if t in (0, 1): return t
        return math.pow(2, 10 * t) * 0.001
    Expo = Symmetric(_expo_in)



class _PerformanceTester(object):
    def __init__(self, a, b, c):
        self.a = a
        self.b = b
        self.c = c

if __name__ == "__main__":
    import datetime as dt

    tweener = Tweener()
    objects = []
    for i in range(10000):
        objects.append(_PerformanceTester(dt.datetime.now(), i-100, i-100))


    total = dt.datetime.now()

    t = dt.datetime.now()
    for i, o in enumerate(objects):
        tweener.add_tween(o, a = dt.datetime.now() - dt.timedelta(days=3), b = i, c = i, duration = 1.0)
    print "add", dt.datetime.now() - t

    tweener.finish()
    print dt.datetime.now() - total
