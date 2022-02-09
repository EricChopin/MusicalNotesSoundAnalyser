########################################################################################
# Author Eric Chopin, January 2021
# Created with pythonista on an iPad2 /iOS12 
# This program analyzes the frequencies received by the microphone 
# and in case it detects some musical notes, it indicates them 
# on a graph, with the relative error with respect to the expected frequency.
# Tested with relative success on an upright piano, the error on the dominant note 
# was less than an half tone.
########################################################################################

from objc_util import *
import ctypes
import numpy as np
import matplotlib.image
import matplotlib.pyplot as plt
import io,ui,console

n=('A','A#','B','C','C#','D','D#','E','F','F#','G','G#')

f=(27.5,29.135235,30.867706,32.703195,34.647829,36.708096,38.890872,41.203444,43.653529,46.249302,48.999429,51.913087)
nfull=[]
ffull=[]

#Array of notes frequencies (tempered scale)
for i in range(10):
	for j in range(12):
		nfull.append(n[j]+str(i))
		ffull.append(f[j]*2**i)
#print(nfull)
#print(ffull)
console.clear()
bRecording=False

#Variables used for peak detection 
wHalfSize=5
wsize=2*wHalfSize+1 #an average is computed over wsize successive values of B
movingSum=0.0 # = B[f]+B[f+1]+.....+B[f+wsize-1]
hwm=0.0 #maximum value of B in wsize successive values   
targetIndex=0
k=3.0 #A peak is detected if the local maximum is above k times the average of wsize values around this maximum
a=12/np.log(2)
b=np.log(440) #440 Hz = A  on the 4th octave 


AVAudioEngine=ObjCClass('AVAudioEngine')
AVAudioSession=ObjCClass('AVAudioSession')

	
error=ctypes.c_void_p(0)
session=AVAudioSession.sharedInstance()
category=session.setCategory('AVAudioSessionCategoryPlayAndRecord',error=ctypes.pointer(error))
if error:
	raise Exception('error setting up category')
session.setActive(True, error=ctypes.pointer(error))
if error:
	raise Exception('error setting up session active')
engine=AVAudioEngine.new()

class fftview(ui.View):
	def button_tapped(self,sender):
		global bRecording
		if bRecording==False:
			bRecording=True
			self.button.title='Stop'
			engine.inputNode().installTapOnBus(0,
						bufferSize=64*256,
						format=None,
						block=process_block)
			engine.startAndReturnError_(None)
		else:
			bRecording=False
			self.button.title='Rec'
			print('stopping engine')
			engine.pause()
	
	def __init__(self,*args,**kwargs):
		ui.View.__init__(self,*args,**kwargs)
		self.i=ui.ImageView()
		self.i.frame=self.bounds
		self.i.flex='wh'
		self.add_subview(self.i)
		self.button= ui.Button(title='Rec')
		self.button.border_width=1
		self.button.corner_radius=5
		self.button.border_color='#efab12'
		self.button.x= 10
		self.button.y= 10
		self.button.width=50
		self.button.height=20
		self.add_subview(self.button)
		self.button.action = self.button_tapped
		
	def update(self,im):
		self.i.image=im
	@ui.in_background
	def will_close(self):
		print('stopping engine')
		engine.pause()
		
v=fftview(frame=(0,0,900,700))


'''setup a tap block'''
buf=[] #for debugging
bIO=io.BytesIO()
lastt=0
def processBuffer(self,buffer,when, cmd):
	global buf, lastt
	buf=ObjCInstance(buffer )
	t=ObjCInstance(when).sampleTime()/44100.
	A=np.ctypeslib.as_array(buf.floatChannelData()[0],(128*128,))
	
	#B=np.log10(abs(np.fft.fft(A,128*128)))
	B=abs(np.fft.fft(A,128*128))
	freq=np.fft.fftfreq(128*128)*44100
	plt.clf()
	plt.plot(freq[:4096],B[:4096])
	plt.ylim(0,100)
	for i in range(10):
		for j in range(12):
			if j==0:
				plt.axvline(ffull[i*10+j],color='r')
			else:
				plt.axvline(ffull[i*10+j])
			
	#Peak detection
	movingSum=0.0
	hwm=0.0
	targets=[]
	for f1 in range(4096):
		movingSum+= B[f1]
		if f1+1>wsize:
			movingSum-=B[f1-wsize]
			hwm=0.0
			for f2 in range(f1-wsize+1,f1+1):
				if B[f2]>hwm:
					hwm=B[f2]
					targetIndex=f2
			if targetIndex==f1 - wHalfSize and hwm * wsize > k * movingSum:
				n0=48+a*(np.log(freq[f2])-b)
				n1=round(n0)
				noteError=int(abs(n1-n0)*100)
				targets.append([int(freq[f2]*10)/10.0,nfull[int(n1)],hwm,noteError])
	if len(targets)>0:
		targets2= sorted(targets, key=lambda x: x[2],reverse=True)
		targets3=[]
		hwm1=targets2[0][2]
		for t in targets2:
			targets3.append([t[0],t[1],int(t[2]/hwm1*1000)/10.0,t[3]])
		print('Notes found:')
		print(targets3)
	#fin calcul des pics
	
	plt.savefig(bIO)
	img=ui.Image.from_data(bIO.getvalue())
	v.update(img)
	bIO.seek(0)
	
	
process_block=ObjCBlock(processBuffer,restype=None,argtypes=[c_void_p,c_void_p,c_void_p,c_void_p])


v.present('sheet')
