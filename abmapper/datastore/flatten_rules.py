FLATTEN_RULES = {
	"XM-DAC-41114": {
        "flatten_down": False,
		"flatten_from": ["2"],
		"flatten_to": "1",
		"flatten_from_fields": {
			"2": ["transaction", "location", "budget"]
		}
	},
	"XI-IATI-EC_DEVCO": {
        "flatten_down": True,
		"flatten_from": ["1"],
		"flatten_to": "2",
		"flatten_from_fields": {
			"1": []
		}
	}
}