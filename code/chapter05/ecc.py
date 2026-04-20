import hashlib

A = 0
B = 7
P = 2**256 - 2**32 - 977
N = 0xfffffffffffffffffffffffffffffffebaaedce6af48a03bbfd25e8cd0364141

#Simple double hash256 function
def sha256(s)-> bytes:
    return hashlib.sha256(s).digest()
#Simple double hash256 function
def hash256(s)-> bytes:
    return hashlib.sha256(hashlib.sha256(s).digest()).digest()

def tagged_hash(data: bytes, tag: str) -> bytes:
    # Compute tag hash
    tag_hash = sha256(tag.encode())
    
    # Compute tagged hash
    contact = tag_hash + tag_hash + data
    return sha256(contact)
## ## Here will be classes for the field element, curve points etc for a more rubust system.
class FieldElementS256:
    def __init__(self, num: int):
        if num is not None:
            if num >= P or num < 0:
                error = 'Num {} not in the S256k1 field range'.format(
                    num)
                raise ValueError(error)
        self.num: int = num
    def __repr__(self):
        return 'S256FieldElement_({})'.format(self.num)
    def __eq__(self, other: 'FieldElementS256') -> bool:
        if type(other) is not type(self):
            return False
        return self.num == other.num
    def __ne__(self, other: 'FieldElementS256')-> bool:
        # this should be the inverse of the == operator
        return not (self.num == other.num)
    def __add__(self, other: 'FieldElementS256')-> 'FieldElementS256':
        if type(self) != type(other):
            raise TypeError('Cannot add two numbers in different Fields')

        # self.num and other.num are the actual values
        # P is what we need to mod against
        if self.num is not None and other.num is not None:
            # We return an element of the same class
            return self.__class__((self.num + other.num) % P)
        elif self.num is None and other.num is not None:
            return self.__class__(other.num)
        elif self.num is not None and other.num is None:
            return self.__class__(self.num)
        elif self.num is None and other.num is None:
            raise TypeError('Some NoneType values encountered')
            #return self.__class__(None)
        else:
            raise TypeError('Some NoneType values encountered')
    def __sub__(self, other: 'FieldElementS256')-> 'FieldElementS256':
        if type(self) != type(other):
            raise TypeError('Cannot subtract two numbers in different Fields')
        
        # self.num and other.num are the actual values
        # P is what we need to mod against
        if self.num is not None and other.num is not None:
            # We return an element of the same class
            return self.__class__((self.num - other.num) % P)
        else:
            raise TypeError('Cannot subtract NoneType values')
        ##addressing for None values
    def __mul__(self, other: 'FieldElementS256')-> 'FieldElementS256':
        if type(self) != type(other):
            raise TypeError('Cannot multiply two numbers in different Fields')
        
        # self.num and other.num are the actual values
        # P is what we need to mod against
        if self.num is not None and other.num is not None:
            # We return an element of the same class
            return self.__class__((self.num * other.num) % P)
        ##addressing for None values
        else:
            raise TypeError('Cannot multiply NoneType values')
        ##addressing for None values
    def __pow__(self, exponent: int)-> 'FieldElementS256':
        # self.num and other.num are the actual values
        # P is what we need to mod against
        if self.num is not None:
            n: int = exponent % (P - 1)
            num: int = pow(self.num, n, P)
            return self.__class__(num)
        ##addressing for None values
        else:
            raise TypeError('Cannot multiply NoneType values')
    def __truediv__(self, other: 'FieldElementS256')-> 'FieldElementS256':
        if type(self) != type(other):
            raise TypeError('Cannot divide two numbers in different Fields')
        # self.num and other.num are the actual values
        # P is what we need to mod against
        if self.num is not None and other.num is not None:
            # use fermat's little theorem:
            # self.num**(p-1) % p == 1
            # this means:
            # 1/n == pow(n, p-2, p)
            # We return an element of the same class
            return self.__class__((self.num * pow(other.num, P - 2, P)) % P)
        ##addressing for None values
        else:
            raise TypeError('Cannot divide NoneType values')
    def __rmul__(self, coefficient: int)-> 'FieldElementS256':
        # self.num and other.num are the actual values
        # P is what we need to mod against
        if self.num is not None:
            return self.__class__((self.num * coefficient) % P)
        else:
            raise TypeError('Cannot multiply NoneType values')
    def sqrt(self)-> 'FieldElementS256':
        # self.num and other.num are the actual values
        # P is what we need to mod against
        if self.num is not None:
            result = pow(self, ((P + 1) //4))

            return  result#self**((P + 1) // 4) 
        
        ##addressing for None values
        else:
            raise TypeError('Cannot square root NoneType values')
    def __mod__(self, coefficient: int)-> 'FieldElementS256':
        if self.num is not None:
            return self.__class__(self.num % coefficient)
        else:
            raise TypeError('Cannot mod NoneType values')
    
    
class Point:
    def __init__(self, x, y):
        self.b = FieldElementS256(B)
        self.x = FieldElementS256(x)
        self.y = FieldElementS256(y)
        self.y_is_even: bool = False
        
        if y is not None:
            if y % 2 == 0:
                
                self.y_is_even: bool = True
            
         
        self.is_infinity = True if (self.x.num == None) and (self.y.num == None) else False
        # x being None and y being None represents the point at infinity
        # Check for that here since the equation below won't make sense
        # with None values for both.
        if (self.x.num is None) != (self.y.num is None):
            raise ValueError('Invalid point: ({}, {})\nEither both coordinates are None or neither are None'.format(x, y))
        # make sure that the elliptic curve equation is satisfied
        # y**2 == x**3 + a*x + b
        if self.x.num is None and self.y.num is None:
            # point at infinity, do nothing
            pass
        else:
            if self.y**2 != self.x**3 + self.b:
                # if not, throw a ValueError
                raise ValueError('({}, {}) is not on the curve'.format(x, y))
    def __repr__(self):
        if self.x.num is None and self.y.num is None:
            return 'Point(infinity)'
        elif self.x.num is not None and self.y.num is not None:
            return 'Secp256k1 Point({},{}) - is even: {}'.format(
                self.x.num, self.y.num, 
                self.y_is_even)
    def __eq__(self, other: 'Point')-> bool:
        if type(other) is not type(self):
            return False
        """Equality operator."""
        if not isinstance(other, Point):
            return NotImplemented
        
        # Both are infinity
        if self.is_infinity and other.is_infinity:
            return True
        
        # One is infinity, the other is not
        if self.is_infinity != other.is_infinity:
            return False
        
        # Both are regular points - compare values
        return (
            self.x == other.x and 
            self.y == other.y
        )
    def __ne__(self, other: 'Point')-> bool:
        if type(other).__name__ != 'Point':
            return NotImplemented
        return not (self == other)
    def __add__(self, other: 'Point')-> 'Point':
        # Case 0.0: self is the point at infinity, return other
        
        if self.x.num is None:
            return other
        
        # Case 0.1: other is the point at infinity, return self
        if other.x.num is None:
            return self
        
        # Case 1: self.x == other.x, self.y != other.y
        # Result is point at infinity
        if self.x == other.x and self.y != other.y:
            return self.__class__(None, None)

        # Case 2: self.x ≠ other.x
        # Formula (x3,y3)==(x1,y1)+(x2,y2)
        # s=(y2-y1)/(x2-x1)
        # x3=s**2-x1-x2
        # y3=s*(x1-x3)-y1
        if self.x != other.x:
            s1: FieldElementS256 = (other.y - self.y) / (other.x - self.x)
            x1: FieldElementS256  = s1**2 - self.x - other.x
            y1: FieldElementS256  = s1 * (self.x - x1) - self.y
            result = self.__class__(x1.num, y1.num)
            #result.update_y_evenness
            return result

        # Case 4: if we are tangent to the vertical line,
        # we return the point at infinity
        # note instead of figuring out what 0 is for each type
        # we just use 0 * self.x
        if self == other and self.y == 0 * self.x:
            return self.__class__(None, None)

        # Case 3: self == other
        # Formula (x3,y3)=(x1,y1)+(x1,y1)
        # s=(3*x1**2+a)/(2*y1)
        # x3=s**2-2*x1
        # y3=s*(x1-x3)-y1
        if self == other:
            s2: FieldElementS256 = (3 * self.x**2) / (2 * self.y)
            x2: FieldElementS256 = s2**2 - 2 * self.x
            y2: FieldElementS256 = s2 * (self.x - x2) - self.y
            return self.__class__(x2.num, y2.num)
        return self.__class__(None, None)
    def __rmul__(self, coefficient: int)-> 'Point':
        coef: int = coefficient
        current: 'Point' = self
        result: 'Point' = self.__class__(None, None)
        
        while coef:
            if coef & 1:
                result += current
            current += current
            coef >>= 1
        return result
    def export_pubkey(self, taproot: bool = False) -> bytes: ##This exports the simple pubkey from the point 

        if not self.x.num is None and taproot:
            return self.x.num.to_bytes(32, 'big')
        elif not self.x.num is None and not taproot:
            if self.is_y_even() == True:
                prefix: bytes = b'\x02'
            elif self.is_y_even() == False:
                prefix: bytes = b'\x03'
            else:
                
                raise ValueError("For some reason, its niether even or odd...")
            return (prefix + self.x.num.to_bytes(32, 'big'))
        else:
            raise Exception("Cannot export pubkey without a point")
    
    
    @classmethod
    def from_pubkey(cls, pubkey: bytes):
        #Extract x coordinate
        
        x_coord: int = int.from_bytes(pubkey[0:32], 'big') if len(pubkey) == 32 else int.from_bytes(pubkey[1:33], 'big')
        x = FieldElementS256(x_coord)
        # right side of the equation y^2 = x^3 + 7
        alpha = x**3 + FieldElementS256(B)
        # solve for left side
        beta = alpha.sqrt()

        if pow(beta,2) != alpha:
            raise ValueError("This point is not on the curve")
        
        ##Calculate if the base y coordinate is odd or even

        if beta.num % 2 == 0:
            y_coord_even: int = beta.num
            y_coord_odd: int = P - beta.num
        else:
            y_coord_even: int = P - beta.num
            y_coord_odd: int = beta.num
        
        if len(pubkey) == 33:
            if pubkey[0] == 2 or pubkey[0] == 0:
                y_coord: int = y_coord_even
            elif pubkey[0] == 3:
                y_coord: int = y_coord_odd
            elif pubkey[0] == 4:
                x_coord: int = int.from_bytes(pubkey[1:33], 'big')
                y_coord: int = int.from_bytes(pubkey[33:], 'big')
                return cls(x_coord,y_coord)
            else:
                raise Exception("invalid pubkey")
        else:
            y_coord: int = y_coord_even
        
        return cls(x_coord,y_coord)

    @classmethod
    def from_priv(cls, key: bytes) -> 'Point':
        k: int = int.from_bytes(key,'big')
        #resulting_point.update_y_evenness()
        return k*G #resulting_point
    #Not sure if this is nessary, but here it is for now.
    
    def is_y_even(self) :
        
        odd_or_even = self.y % 2
        if odd_or_even == FieldElementS256(0):
            return True
        else:
            return False
    
G = Point(
    0x79be667ef9dcbbac55a06295ce870b07029bfcdb2dce28d959f2815b16f81798,
    0x483ada7726a3c4655da4fbfc0e1108a8fd17b448a68554199c47d08ffb10d4b8)
