from numpy                          import abs, zeros, pad, array, expand_dims, concatenate, median, append
import scipy.signal
import socket
import json
import time
from threading                      import Thread

class Backend:

    def __init__(self):
        # =================================================================
        # Initialize receiver
        # -----------------------------------------------------------------
        # - Initialize zero buffer: self.buffer
        # - Initialize time stamps array of zeros: self.time_stamps
        # =================================================================

        # Set streaming parameters
        self.ip             = '127.0.0.1' # Localhost, requires Neuri GUI running
        self.port           = 12344
        self.sample_rate    = 200 # Hz

        # Set buffer parameters
        self.buffer_length  = 5 # s
        self.num_channels   = 2 # Neuri boards V1.0
        self.target_chan    = 0 # First channel
        self.count          = 0

        # Stop recording
        self.stop           = False
        
        # Initialize zeros buffer and time stamps
        self.buffer         = self.prep_buffer(self.buffer_length * self.sample_rate)

        # =================================================================
        # Initialize signal processing
        # -----------------------------------------------------------------
        # - signal features
        # - filters
        # =================================================================
        self.filter_order   = 3 #scalar
        self.frequency_bands= {
            'Workshop':     (0.05,  6),
            'LineNoise':    (46,    54)}

        self.min_value      = 0
        self.max_value      = 0
        self.turn_threshold = 0.5 # How much of the min or max value has to be reached to trigger a turn
        
        self.prepare_filters()
        self.receiver_socket = self.prepare_socket(self.ip, self.port)

        
    def prep_buffer(self, length):
        # This functions creates the buffer structure
        # that will be filled with eeg datasamples
        return zeros(length)


    def prep_time_stamps(self, length):
        return zeros(length)
    

    def prepare_socket(self, ip, port):
        
        # Setup UDP protocol: connect to the UDP EEG streamer
        receiver_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        receiver_sock.bind((ip, int(port)))

        return receiver_sock


    def get_sample(self, readin_connection):

        valid_eeg = False
        # Get eeg samples from the UDP streamer
        raw_message, _  = readin_connection.recvfrom(1024)

        try:
            eeg_dict    = json.loads(raw_message)  # Vector with length self.num_channel
            eeg_data    = array([float(eeg_dict["c1"]), float(eeg_dict["c2"])])
            eeg_data    = expand_dims(eeg_data, 1)
            valid_eeg   = True
        except:
            eeg_data    = array([0.0, 0.0])
            print("Skipped message")
        
        return eeg_data, valid_eeg


    def fill_buffer(self, sending_pipe, conn_socket):
        # This functions fills the buffer in self.buffer
        # that later can be accesed to perfom the real time analysis
        
        for _ in range(500):
            # Dirty way to empty the buffer at socket
            _, _  = conn_socket.recvfrom(1024)

        with conn_socket as r:

            while not self.stop:
                    
                # Get samples
                sample, valid       = self.get_sample(r)

                if not valid:
                    continue

                # Concatenate vector
                update_buffer       = concatenate((self.buffer, sample[self.target_chan]), axis=0)

                # save to new buffer
                self.buffer         = update_buffer[1:]

                filtered_buffer     = self.process_buffer()

                direction_change    = self.direction_change(filtered_buffer) # -1 left, 0 no change, 1 right

                # Push to frontend
                sending_pipe.send((direction_change))

        self.receiver_sock.close()
        return


    def start_receiver(self, sending_pipe, conn_socket):
        # Define thread for receiving
        self.receiver_thread = Thread(
            target=self.fill_buffer,
            name='receiver_thread',
            daemon=False,
            args=(sending_pipe, conn_socket))
        # start thread
        self.receiver_thread.start()


    def stop_receiver(self, readin_connection):
        # Change the status of self.stop to stop the recording
        self.stop = True
        readin_connection.close()
        time.sleep(2)  # Wait two seconds to stop de recording to be sure that everything stopped


    def prepare_filters(self):

        # Bandpass filters
        # -----------------------------------------------------------------
        self.b_workshop, self.a_workshop        = scipy.signal.butter(
            self.filter_order, self.frequency_bands["Workshop"][0],
            btype='highpass', fs=self.sample_rate)
        self.b_notch, self.a_notch              = scipy.signal.butter(
            self.filter_order, self.frequency_bands["LineNoise"],
            btype='bandstop', fs=self.sample_rate)

        # Determine padding length for signal filtering
        # -----------------------------------------------------------------
        default_pad     = 3 * max(len(self.a_workshop), 
            len(self.b_workshop))
        if default_pad > self.buffer_length * self.sample_rate/10-1:
            self.padlen = int(default_pad) # Scipy expects int
        else:
            self.padlen = int(self.buffer_length*self.sample_rate/10-1) # Scipy expects int


    def filter_signal(self, signal, b, a):
        # =================================================================
        # Input:
        #   signal              Numpy 1D array [samples]
        # Output:
        #   signal_filtered[0]  1D numpy array of filtered signal where 
        #                       first sample is 0
        # =================================================================
        padded_signal   = pad(signal, (self.padlen, 0), 'symmetric')
        init_state      = scipy.signal.lfilter_zi(b, a) # 1st sample --> 0
        signal_filtered = scipy.signal.lfilter(b, a, padded_signal, 
            zi=init_state*padded_signal[0])
        signal_filtered = signal_filtered[0][self.padlen:]
        return signal_filtered
    

    def process_buffer(self):
        # =================================================================
        # Input:
        #   buffer              Numpy array [channels x samples]
        #   bSB, aSB            Filter coefficients as put out by 
        #                       scipy.signal.butter (Stopband)
        #   bPB, aPB            Filter coefficients as put out by 
        #                       scipy.signal.butter (Passband)
        # Output:
        #   filtered_buffer     Numpy array of filtered signal, same  
        #                       dimensions as input buffer
        # =================================================================
        noise_free_signal   = zeros(self.buffer.size)
        filtered_buffer     = zeros(self.buffer.size)

        # Reject ambiant electrical noise (at 50 Hz)
        # -------------------------------------------------------------
        noise_free_signal = self.filter_signal(self.buffer, self.b_notch, self.a_notch)
        
        # Extract useful frequency range
        # -------------------------------------------------------------
        filtered_buffer = self.filter_signal(noise_free_signal, self.b_workshop, self.a_workshop)

        return filtered_buffer
    

    def direction_change(self, signal):
        med_value = median(signal[-int(self.sample_rate/2):])

        if med_value < self.min_value:
            self.min_value = med_value
        if med_value > self.max_value:
            self.max_value = med_value

        # print(self.min_value)
        # print(self.max_value)
        
        # self.count = self.count + 1
        # if self.count == self.sample_rate:
        #     print(med_value)
        #     self.count = 0

        if med_value > self.turn_threshold * self.max_value:
            return 1
        elif med_value < self.turn_threshold * self.min_value:
            return -1
        else:
            return 0
        