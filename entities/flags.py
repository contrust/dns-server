from dataclasses import dataclass


@dataclass
class Flags:
    def __init__(self, qr: int, opcode: int, aa: int, tc: int,
                 rd: int, ra: int, z: int, reply_code: int):
        self.qr = qr
        self.opcode = opcode
        self.aa = aa
        self.tc = tc
        self.rd = rd
        self.ra = ra
        self.z = z
        self.reply_code = reply_code

    @staticmethod
    def parse(line: str):
        params = "{:b}".format(int(line, 16)).zfill(16)
        return Flags(int(params[0:1], 16), int(params[1:5], 16),
                     int(params[5:6], 16),
                     int(params[6:7], 16),
                     int(params[7:8], 16), int(params[8:9], 16),
                     int(params[9:12], 16),
                     int(params[12:16], 16))

    def __str__(self):
        result = str(self.qr)
        result += str(self.opcode).zfill(4)
        result += str(self.aa) + str(self.tc) + str(self.rd) + str(self.ra)
        result += str(self.z).zfill(3)
        result += str(self.reply_code).zfill(4)
        result = "{:04x}".format(int(result, 2))
        return result
