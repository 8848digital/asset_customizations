def on_submit(self):
	self.validate_in_use_date()
	self.set_status()
	self.make_asset_movement()
	self.reload()
