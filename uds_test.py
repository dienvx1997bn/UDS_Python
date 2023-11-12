import serial
import threading
import time

import ctypes
kernel32 = ctypes.windll.kernel32


UDS_PING_CMD = bytearray([0x81, 0x10, 0xF1, 0x81, 0x03])
UDS_READID_CMD = bytearray([0x82, 0x10, 0xF1, 0x1A, 0x80, 0x1D])

UDS_START_DIAG_CMD = bytearray([0x83, 0x10, 0xF1, 0x10, 0x84, 0x04, 0x1C])
UDS_REQ_KEY_CMD = bytearray([0x80, 0x10, 0x01, 0x02, 0x27, 0x09, 0xC3])
UDS_RESP_KEY_CMD = bytearray([0x80, 0x10, 0x01, 0x06, 0x27, 0x0A])
UDS_REQ_READ_EEPROM_CMD = bytearray([0x80, 0x10, 0x01, 0x02, 0x35, 0x22, 0xEA])
UDS_READ_EEPROM_CMD = bytearray([0x80, 0x10, 0x01, 0x06, 0x36, 0x22])


ser = serial.Serial('COM6', 10400, timeout=2)
seedkey_pass = False

def accurate_delay(delay):
    ''' Function to provide accurate time delay in millisecond
    '''
    _ = time.perf_counter() + delay/1000
    while time.perf_counter() < _:
        pass


def data_print(data):
    print(' '.join([hex(b) for b in data]))

def init_kline():
    ser.baudrate = 350
    ser.timeout = 1
    ser.write(b'\x00')
    #####
    accurate_delay(55)
    #####
    ser.baudrate = 10400
    ser.timeout = 1
    ser.write(UDS_PING_CMD)
    reads = ser.read(13)

    #small delay
    time.sleep(0.05)

    check_String = b'\x83\xf1\x10\xc1\xef\x8f\xc3'
    if check_String in reads:
        return True
    return False


def data_caculate_crc(arr):
    total_sum = sum(arr)
    result_byte = total_sum & 0xFF
    return bytearray([result_byte])


def data_read(expected_len):
    buffer = bytearray()  # Bộ đệm
    # ser.reset_input_buffer()
    count = 0

    while count < expected_len:
        data = ser.read(1)  # Đọc từng byte
        if data:
            buffer += data
            count += 1
            # print("data_read ", count, " data ", data)

    # print("data_read: ",buffer)
    return buffer


def UDS_trans_cmd(data, isheader4 = False):
    ser.baudrate = 10400
    ser.timeout = 1
    ser.write(data)
    ser.read(len(data))

    if isheader4 == False:
        reads = data_read(1)
        start_byte = reads[0]
        if start_byte > 128:
            length = start_byte - 128 + 4 - 1
        else:
            length = 128 - start_byte + 4 - 1
    else:
        reads = data_read(4)
        length = reads[3] + 1 
    
    # print("expect read length: ",length)
    reads = reads + data_read(length)
    print("send ")
    data_print(data)
    print("recv ")
    data_print(reads)
    print("-----------------------")

    #small delay
    time.sleep(0.1)
    # ser.reset_output_buffer()
    return reads


def seedKey_response(seed0, seed1):
    temp = (seed1 + 1) * 1.44
    temp2 = int((seed0 * 256 + seed1) / 200) * 200

    key0 = (int(temp) + 1) & 0xFF
    temp2 = temp2 & 0xFF
    temp2 = seed1 - temp2
    key1 = temp2 & 0xFF

    return bytearray([key0, key1])



def main():
    global seedkey_pass

    print("Init connection")
    for i in range(10):
        time.sleep(0.2)
        ret = init_kline()
        if ret:
            print("Init K-line success")
            time.sleep(0.15)
            break
        else:
            print("Try to init K-line in " + str(i) + " time")

    print("Read device info")
    UDS_trans_cmd(UDS_READID_CMD, isheader4=False)
    print("start diagnostic")
    UDS_trans_cmd(UDS_START_DIAG_CMD, isheader4=False)

    print("Seed - Key process")
    byte_recv = UDS_trans_cmd(UDS_REQ_KEY_CMD, isheader4=True)
    byte_resp = seedKey_response(byte_recv[6], byte_recv[7])
    data_print(byte_resp)
    UDS_RESP_KEY_CMD.extend(byte_resp)
    UDS_RESP_KEY_CMD.extend(bytearray([0x37, 0x54]))
    UDS_RESP_KEY_CMD.extend(data_caculate_crc(UDS_RESP_KEY_CMD))
    byte_resp = UDS_trans_cmd(UDS_RESP_KEY_CMD, isheader4=True)
    if bytearray([0x80, 0x01, 0x10, 0x03, 0x67, 0x0A, 0x34, 0x39]) in byte_resp:
        print("Seed - Key success!!")
        seedkey_pass = True
    else:
        print("Seed - Key fail :(")

    if seedkey_pass == True:
        UDS_trans_cmd(UDS_REQ_READ_EEPROM_CMD, isheader4=True)
        for i in range(128):
            UDS_READ_EEPROM_CMD.extend(bytearray([0x00, i//256, i%256, 0x20]))
            UDS_READ_EEPROM_CMD.extend(data_caculate_crc(UDS_READ_EEPROM_CMD))
            byte_recv = UDS_trans_cmd(UDS_READ_EEPROM_CMD, isheader4=True)
            i += 32



if __name__ == "__main__":
    main()
    ser.close()
