import serial

def listener(ser, q):
    print(f'Listener on {ser.port}...')
    while True:
        try:
            line = ser.readline().decode(errors='ignore').strip()
            if line:
                q.put(line)
        except serial.SerialException as e:
            print(f"Serial read error: {e}")
            break

def writer(ser, q, lock):
    print(f'Writer on {ser.port}...')
    while True:
        try:
            data = q.get()  # blocking until item available
            if isinstance(data, str):
                data = data.encode()
            with lock:
                ser.write(data)
                ser.flush()
                print(f'Sending: {data}')
        except serial.SerialException as e:
            print(f"Serial write error: {e}")
            break
        except Exception as e:
            print(f"Unexpected writer error: {e}")
            break
