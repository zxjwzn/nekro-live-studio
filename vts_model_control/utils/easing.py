import math

class Easing:
    @staticmethod
    def linear(t: float) -> float:
        """线性缓动函数，直接返回 t"""
        return t

    @staticmethod
    def in_sine(t):
        return math.sin(1.5707963 * t)

    @staticmethod
    def out_sine(t):
        return 1 + math.sin(1.5707963 * (t - 1))

    @staticmethod
    def in_out_sine(t):
        return 0.5 * (1 + math.sin(3.1415926 * (t - 0.5)))

    @staticmethod
    def in_quad(t):
        return t * t

    @staticmethod
    def out_quad(t):
        return t * (2 - t)

    @staticmethod
    def in_out_quad(t):
        return 2 * t * t if t < 0.5 else t * (4 - 2 * t) - 1

    @staticmethod
    def in_cubic(t):
        return t * t * t

    @staticmethod
    def out_cubic(t):
        t = t - 1
        return 1 + t * t * t

    @staticmethod
    def in_out_cubic(t):
        if t < 0.5:
            return 4 * t * t * t
        else:
            t = t - 1
            return 1 + (t) * (2 * (t)) * (2 * t)

    @staticmethod
    def in_quart(t):
        t *= t
        return t * t

    @staticmethod
    def out_quart(t):
        t = (t - 1) * t
        return 1 - t * t

    @staticmethod
    def in_out_quart(t):
        if t < 0.5:
            t *= t
            return 8 * t * t
        else:
            t = (t - 1) * t
            return 1 - 8 * t * t

    @staticmethod
    def in_quint(t):
        t2 = t * t
        return t * t2 * t2

    @staticmethod
    def out_quint(t):
        t -= 1
        t2 = t * t
        return 1 + t * t2 * t2

    @staticmethod
    def in_out_quint(t):
        if t < 0.5:
            t2 = t * t
            return 16 * t * t2 * t2
        else:
            t -= 1
            t2 = t * t
            return 1 + 16 * t * t2 * t2

    @staticmethod
    def in_expo(t):
        return (pow(2, 8 * t) - 1) / 255

    @staticmethod
    def out_expo(t):
        return 1 - pow(2, -8 * t)

    @staticmethod
    def in_out_expo(t):
        if t < 0.5:
            return (pow(2, 16 * t) - 1) / 510
        else:
            return 1 - 0.5 * pow(2, -16 * (t - 0.5))

    @staticmethod
    def in_circ(t):
        return 1 - math.sqrt(1 - t)

    @staticmethod
    def out_circ(t):
        return math.sqrt(t)

    @staticmethod
    def in_out_circ(t):
        if t < 0.5:
            return (1 - math.sqrt(1 - 2 * t)) * 0.5
        else:
            return (1 + math.sqrt(2 * t - 1)) * 0.5

    @staticmethod
    def in_back(t):
        return t * t * (2.70158 * t - 1.70158)

    @staticmethod
    def out_back(t):
        t -= 1
        return 1 + t * t * (2.70158 * t + 1.70158)

    @staticmethod
    def in_out_back(t):
        if t < 0.5:
            return t * t * (7 * t - 2.5) * 2
        else:
            t -= 1
            return 1 + t * t * 2 * (7 * t + 2.5)

    @staticmethod
    def in_elastic(t):
        t2 = t * t
        return t2 * t2 * math.sin(t * math.pi * 4.5)

    @staticmethod
    def out_elastic(t):
        t2 = (t - 1) * (t - 1)
        return 1 - t2 * t2 * math.cos(t * math.pi * 4.5)

    @staticmethod
    def in_out_elastic(t):
        if t < 0.45:
            t2 = t * t
            return 8 * t2 * t2 * math.sin(t * math.pi * 9)
        elif t < 0.55:
            return 0.5 + 0.75 * math.sin(t * math.pi * 4)
        else:
            t2 = (t - 1) * (t - 1)
            return 1 - 8 * t2 * t2 * math.sin(t * math.pi * 9)

    @staticmethod
    def in_bounce(t):
        return pow(2, 6 * (t - 1)) * abs(math.sin(t * math.pi * 3.5))

    @staticmethod
    def out_bounce(t):
        return 1 - pow(2, -6 * t) * abs(math.cos(t * math.pi * 3.5))

    @staticmethod
    def in_out_bounce(t):
        if t < 0.5:
            return 8 * pow(2, 8 * (t - 1)) * abs(math.sin(t * math.pi * 7))
        else:
            return 1 - 8 * pow(2, -8 * t) * abs(math.sin(t * math.pi * 7))