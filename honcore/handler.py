packets = {}
events = {}

def packet_handler(packet_id):
	def register_handler(f):
		if packet_id in packets:
			return f
		packets[packet_id] = f
		return f
	return register_handler

def event_handler(event_name):
	def register_handler(f):
		events[event_name] = f
		return f
	return register_handler
