packets = {}
events = {}

def packet(packet_id):
	def register_handler(f):
		if packet_id in packets:
			return f
		packets[packet_id] = f
		return f
	return register_handler

def event(event_type):
	def register_handler(f):
		events[event_type] = f
		return f
	return register_handler
