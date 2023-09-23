"""\
A streamlit app visualizing the JSON checker parsing process. 

This app ports the C JSON checker from https://www.json.org/JSON_checker into python.
"""

import streamlit as st
from annotated_text import annotated_text
from st_keyup import st_keyup
from enum import Enum
import pandas as pd

# TRUE = 1
# FALSE = 0
# GOOD = 0xBABAB00E
__ = -1

# Characters are mapped into these 31 character classes. This allows for
# a significant reduction in the size of the state transition table.
C_SPACE = 0  # space */
C_WHITE = 1  # other whitespace */
C_LCURB = 2  # {  */
C_RCURB = 3  # } */
C_LSQRB = 4  # [ */
C_RSQRB = 5  # ] */
C_COLON = 6  # : */
C_COMMA = 7  # , */
C_QUOTE = 8  # " */
C_BACKS = 9  # \ */
C_SLASH = 10  # / */
C_PLUS = 11  # + */
C_MINUS = 12  # - */
C_POINT = 13  # . */
C_ZERO = 14  # 0 */
C_DIGIT = 15  # 123456789 */
C_LOW_A = 16  # a */
C_LOW_B = 17  # b */
C_LOW_C = 18  # c */
C_LOW_D = 19  # d */
C_LOW_E = 20  # e */
C_LOW_F = 21  # f */
C_LOW_L = 22  # l */
C_LOW_N = 23  # n */
C_LOW_R = 24  # r */
C_LOW_S = 25  # s */
C_LOW_T = 26  # t */
C_LOW_U = 27  # u */
C_ABCDF = 28  # ABCDF */
C_E = 29  # E */
C_ETC = 30  # everything else */
NR_CLASSES = 31

ascii_class = [
    # This array maps the 128 ASCII characters into character classes.
    # The remaining Unicode characters should be mapped to C_ETC.
    # Non-whitespace control characters are errors.
    __,      __,      __,      __,      __,      __,      __,      __,
    __,      C_WHITE, C_WHITE, __,      __,      C_WHITE, __,      __,
    __,      __,      __,      __,      __,      __,      __,      __,
    __,      __,      __,      __,      __,      __,      __,      __,
    C_SPACE, C_ETC,   C_QUOTE, C_ETC,   C_ETC,   C_ETC,   C_ETC,   C_ETC,
    C_ETC,   C_ETC,   C_ETC,   C_PLUS,  C_COMMA, C_MINUS, C_POINT, C_SLASH,
    C_ZERO,  C_DIGIT, C_DIGIT, C_DIGIT, C_DIGIT, C_DIGIT, C_DIGIT, C_DIGIT,
    C_DIGIT, C_DIGIT, C_COLON, C_ETC,   C_ETC,   C_ETC,   C_ETC,   C_ETC,
    C_ETC,   C_ABCDF, C_ABCDF, C_ABCDF, C_ABCDF, C_E,     C_ABCDF, C_ETC,
    C_ETC,   C_ETC,   C_ETC,   C_ETC,   C_ETC,   C_ETC,   C_ETC,   C_ETC,
    C_ETC,   C_ETC,   C_ETC,   C_ETC,   C_ETC,   C_ETC,   C_ETC,   C_ETC,
    C_ETC,   C_ETC,   C_ETC,   C_LSQRB, C_BACKS, C_RSQRB, C_ETC,   C_ETC,
    C_ETC,   C_LOW_A, C_LOW_B, C_LOW_C, C_LOW_D, C_LOW_E, C_LOW_F, C_ETC,
    C_ETC,   C_ETC,   C_ETC,   C_ETC,   C_LOW_L, C_ETC,   C_LOW_N, C_ETC,
    C_ETC,   C_ETC,   C_LOW_R, C_LOW_S, C_LOW_T, C_LOW_U, C_ETC,   C_ETC,
    C_ETC,   C_ETC,   C_ETC,   C_LCURB, C_ETC,   C_RCURB, C_ETC,   C_ETC
]

assert len(ascii_class) == 128

# The state codes.
GO = 0  # start    */
OK = 1  # ok       */
OB = 2  # object   */
KE = 3  # key      */
CO = 4  # colon    */
VA = 5  # value    */
AR = 6  # array    */
ST = 7  # string   */
ES = 8  # escape   */
U1 = 9  # u1       */
U2 = 10  # u2       */
U3 = 11  # u3       */
U4 = 12  # u4       */
MI = 13  # minus    */
ZE = 14  # zero     */
IN = 15  # integer  */
FR = 16  # fraction */
FS = 17  # fraction */
E1 = 18  # e        */
E2 = 19  # ex       */
E3 = 20  # exp      */
T1 = 21  # tr       */
T2 = 22  # tru      */
T3 = 23  # true     */
F1 = 24  # fa       */
F2 = 25  # fal      */
F3 = 26  # fals     */
F4 = 27  # false    */
N1 = 28  # nu       */
N2 = 29  # nul      */
N3 = 30  # null     */
NR_STATES = 31

state_to_state_name = [
    'START', 'OK', 'OBJECT', 'KEY', 'COLON', 'VALUE', 'ARRAY',
    'STRING', 'ESCAPE', 'UNICODE-1', 'UNICODE-2', 'UNICODE-3', 'UNICODE-4',
    'MINUS', 'ZERO', 'INTEGER', 'FRACTION-R', 'FRACTION-S', 'EXPONENT-1', 'EXPONENT-2', 'EXPONENT-3',
    'tr', 'tru', 'true', 'fa', 'fal', 'fals', 'false', 'nu', 'nul', 'null', 'INVALID!!!'
]

state_transition_table = [
    # The state transition table takes the current state and the current symbol,
    # and returns either a new state or an action. An action is represented as a
    # negative number. A JSON text is accepted if at the end of the text the
    # state is OK and if the mode is MODE_DONE.

    # /*start  GO*/
    [GO, GO, -6, __, -5, __, __, __, __, __, __, __, __, __, __, __,
     __, __, __, __, __, __, __, __, __, __, __, __, __, __, __],
    # /*ok     OK*/
    [OK, OK, __, -8, __, -7, __, -3, __, __, __, __, __, __, __, __,
     __, __, __, __, __, __, __, __, __, __, __, __, __, __, __],
    # /*object OB*/
    [OB, OB, __, -9, __, __, __, __, ST, __, __, __, __, __, __, __,
     __, __, __, __, __, __, __, __, __, __, __, __, __, __, __],
    # /*key    KE*/
    [KE, KE, __, __, __, __, __, __, ST, __, __, __, __, __, __, __,
     __, __, __, __, __, __, __, __, __, __, __, __, __, __, __],
    # /*colon  CO*/
    [CO, CO, __, __, __, __, -2, __, __, __, __, __, __, __, __, __,
     __, __, __, __, __, __, __, __, __, __, __, __, __, __, __],
    # /*value  VA*/
    [VA, VA, -6, __, -5, __, __, __, ST, __, __, __, MI, __, ZE, IN,
     __, __, __, __, __, F1, __, N1, __, __, T1, __, __, __, __],
    # /*array  AR*/
    [AR, AR, -6, __, -5, -7, __, __, ST, __, __, __, MI, __, ZE, IN,
     __, __, __, __, __, F1, __, N1, __, __, T1, __, __, __, __],
    # /*string ST*/
    [ST, __, ST, ST, ST, ST, ST, ST, -4, ES, ST, ST, ST, ST, ST, ST,
     ST, ST, ST, ST, ST, ST, ST, ST, ST, ST, ST, ST, ST, ST, ST],
    # /*escape ES*/
    [__, __, __, __, __, __, __, __, ST, ST, ST, __, __, __, __, __,
     __, ST, __, __, __, ST, __, ST, ST, __, ST, U1, __, __, __],
    # /*u1     U1*/
    [__, __, __, __, __, __, __, __, __, __, __, __, __, __, U2, U2,
     U2, U2, U2, U2, U2, U2, __, __, __, __, __, __, U2, U2, __],
    # /*u2     U2*/
    [__, __, __, __, __, __, __, __, __, __, __, __, __, __, U3, U3,
     U3, U3, U3, U3, U3, U3, __, __, __, __, __, __, U3, U3, __],
    # /*u3     U3*/
    [__, __, __, __, __, __, __, __, __, __, __, __, __, __, U4, U4,
     U4, U4, U4, U4, U4, U4, __, __, __, __, __, __, U4, U4, __],
    # /*u4     U4*/
    [__, __, __, __, __, __, __, __, __, __, __, __, __, __, ST, ST,
     ST, ST, ST, ST, ST, ST, __, __, __, __, __, __, ST, ST, __],
    # /*minus  MI*/
    [__, __, __, __, __, __, __, __, __, __, __, __, __, __, ZE, IN,
     __, __, __, __, __, __, __, __, __, __, __, __, __, __, __],
    # /*zero   ZE*/
    [OK, OK, __, -8, __, -7, __, -3, __, __, __, __, __, FR, __, __,
     __, __, __, __, E1, __, __, __, __, __, __, __, __, E1, __],
    # /*int    IN*/
    [OK, OK, __, -8, __, -7, __, -3, __, __, __, __, __, FR, IN, IN,
     __, __, __, __, E1, __, __, __, __, __, __, __, __, E1, __],
    # /*frac   FR*/
    [__, __, __, __, __, __, __, __, __, __, __, __, __, __, FS, FS,
     __, __, __, __, __, __, __, __, __, __, __, __, __, __, __],
    # /*fracs  FS*/
    [OK, OK, __, -8, __, -7, __, -3, __, __, __, __, __, __, FS, FS,
     __, __, __, __, E1, __, __, __, __, __, __, __, __, E1, __],
    # /*e      E1*/
    [__, __, __, __, __, __, __, __, __, __, __, E2, E2, __, E3, E3,
     __, __, __, __, __, __, __, __, __, __, __, __, __, __, __],
    # /*ex     E2*/
    [__, __, __, __, __, __, __, __, __, __, __, __, __, __, E3, E3,
     __, __, __, __, __, __, __, __, __, __, __, __, __, __, __],
    # /*exp    E3*/
    [OK, OK, __, -8, __, -7, __, -3, __, __, __, __, __, __, E3, E3,
     __, __, __, __, __, __, __, __, __, __, __, __, __, __, __],
    # /*tr     T1*/
    [__, __, __, __, __, __, __, __, __, __, __, __, __, __, __, __,
     __, __, __, __, __, __, __, __, T2, __, __, __, __, __, __],
    # /*tru    T2*/
    [__, __, __, __, __, __, __, __, __, __, __, __, __, __, __, __,
     __, __, __, __, __, __, __, __, __, __, __, T3, __, __, __],
    # /*true   T3*/
    [__, __, __, __, __, __, __, __, __, __, __, __, __, __, __, __,
     __, __, __, __, OK, __, __, __, __, __, __, __, __, __, __],
    # /*fa     F1*/
    [__, __, __, __, __, __, __, __, __, __, __, __, __, __, __, __,
     F2, __, __, __, __, __, __, __, __, __, __, __, __, __, __],
    # /*fal    F2*/
    [__, __, __, __, __, __, __, __, __, __, __, __, __, __, __, __,
     __, __, __, __, __, __, F3, __, __, __, __, __, __, __, __],
    # /*fals   F3*/
    [__, __, __, __, __, __, __, __, __, __, __, __, __, __, __, __,
     __, __, __, __, __, __, __, __, __, F4, __, __, __, __, __],
    # /*false  F4*/
    [__, __, __, __, __, __, __, __, __, __, __, __, __, __, __, __,
     __, __, __, __, OK, __, __, __, __, __, __, __, __, __, __],
    # /*nu     N1*/
    [__, __, __, __, __, __, __, __, __, __, __, __, __, __, __, __,
     __, __, __, __, __, __, __, __, __, __, __, N2, __, __, __],
    # /*nul    N2*/
    [__, __, __, __, __, __, __, __, __, __, __, __, __, __, __, __,
     __, __, __, __, __, __, N3, __, __, __, __, __, __, __, __],
    # /*null   N3*/
    [__, __, __, __, __, __, __, __, __, __, __, __, __, __, __, __,
     __, __, __, __, __, __, OK, __, __, __, __, __, __, __, __]
]

assert len(state_transition_table) == NR_STATES
assert all(len(row) == NR_CLASSES for row in state_transition_table)


class Modes(Enum):
    MODE_ARRAY = 1
    MODE_DONE = 2
    MODE_KEY = 3
    MODE_OBJECT = 4

    def __str__(self):
        return f'{self.name}'


class JSONChecker:

    def __init__(self, depth=20):
        self.valid = True
        self.state = GO
        self.depth = depth
        self.stack = [Modes.MODE_DONE]

    def push(self, mode):
        if len(self.stack) + 1 >= self.depth:
            return False
        self.stack.append(mode)
        return True

    def pop(self, mode):
        if len(self.stack) == 0:
            return False

        top = self.stack.pop()

        if top != mode:
            return False

        return True

    def _reject(self):
        self.valid = False
        return False

    def consume(self, next_char):

        if not self.valid:
            return False

        char_id = ord(next_char)

        next_class = 0
        next_state = 0

        if char_id < 0:
            return self._reject()

        if char_id >= 128:
            next_class = C_ETC
        else:
            next_class = ascii_class[char_id]
            if next_class <= __:
                return self._reject()

        next_state = state_transition_table[self.state][next_class]

        if next_state >= 0:
            self.state = next_state
            return True
        else:
            match next_state:
                case -9:
                    if not self.pop(Modes.MODE_KEY):
                        return self._reject()
                    self.state = OK
                    pass
                # }
                case -8:
                    if not self.pop(Modes.MODE_OBJECT):
                        return self._reject()
                    self.state = OK
                    pass
                # ]
                case -7:
                    if not self.pop(Modes.MODE_ARRAY):
                        return self._reject()
                    self.state = OK
                    pass
                # {
                case -6:
                    if not self.push(Modes.MODE_KEY):
                        return self._reject()
                    self.state = OB
                    pass
                # [
                case -5:
                    if not self.push(Modes.MODE_ARRAY):
                        return self._reject()
                    self.state = AR
                    pass
                # "
                case -4:
                    match self.stack[-1]:
                        case Modes.MODE_KEY:
                            self.state = CO
                            pass
                        case Modes.MODE_ARRAY:
                            self.state = OK
                            pass
                        case Modes.MODE_OBJECT:
                            self.state = OK
                            pass
                        case _:
                            return self._reject()
                    pass
                # ,
                case -3:
                    match self.stack[-1]:
                        case Modes.MODE_OBJECT:
                            if not self.pop(Modes.MODE_OBJECT) or not self.push(Modes.MODE_KEY):
                                return self._reject()
                            self.state = KE
                            pass
                        case Modes.MODE_ARRAY:
                            self.state = VA
                            pass
                        case _:
                            return self._reject()
                    pass
                # :
                case -2:
                    if not self.pop(Modes.MODE_KEY) or not self.push(Modes.MODE_OBJECT):
                        return self._reject()
                    self.state = VA
                    pass
                case _:
                    return self._reject()
            return True

    def done(self):
        if not self.valid:
            return False

        return self.state == OK and self.stack[-1] == Modes.MODE_DONE


def index_column(stack):
    if len(stack) <= 1:
        return ["top"]
    else:
        index = ["" for _ in range(len(stack))]
        index[0] = "top"
        index[-1] = "bottom"
        return index


def check(string):

    checker = JSONChecker()

    is_valid = True

    for idx, ch in enumerate(string):
        is_valid = checker.consume(ch)

        if not is_valid:
            annotated_text(
                (string[:idx], '<valid>', '#008000'),
                (string[idx:], '<invalid>', '#FF0000')
            )
            st.text(f'State: {state_to_state_name[checker.state]}')
            st.text(f'Stack: {", ".join(str(mode) for mode in checker.stack)}')
            break

    if is_valid:

        col1, col2 = st.columns([3, 1])

        with col1:
            if checker.done():
                annotated_text((string, '<valid>', '#008000'))
            else:
                annotated_text((string, '<valid so far>', '#008000'))

            st.text(f'State: {state_to_state_name[checker.state]}')
            st.dataframe(pd.DataFrame(data={
                "stack (top to bottom)": checker.stack[::-1]
            }, index=index_column(checker.stack)))

        with col2:
            if checker.done():
                st.json(string)


st.title("JSON Checker Visualization")

st.markdown("""
This app checks if a given string is a valid JSON string. 
The code is based on the [JSON checker](https://www.json.org/JSON_checker/), which implements a deterministic pushdown automata (PDA) for parsing JSON.

* When the string is a valid JSON string, the string is highlighted in green color
* When the string is not a valid JSON string, the portion of the string that disagrees with the JSON syntax is highlighted in red.
* Finally, the PDA state and stack are shown
""")

st.text("Input a string in the text box below to check if it is a valid JSON string")

target_string = st_keyup("", value='{"a":1}', label_visibility="hidden")

check(target_string)
