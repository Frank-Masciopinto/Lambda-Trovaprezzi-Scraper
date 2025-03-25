
from flask import Flask, jsonify

app = Flask(__name__)

# Assuming you already have configured the Flask app and database
@app.route('/test', methods=['GET'])
def get_items():
    
    # Create a list of items to return in the response
    items_list = [{"id": 1, "name": "test Frank"}]
    
    return jsonify(items_list)

if __name__ == '__main__':
    app.run(debug=True)

# class Command(BaseCommand):
#     help = 'Run the TrovaPrezzi scraper locally'

    # def add_arguments(self, parser):
    #     parser.add_argument('--venditore', type=str, required=True)
    #     parser.add_argument('--categoria', type=str)

    # def handle(self, *args, **options):
    #     self.stdout.write('Starting scraper...')

        # result = get_pagination_urls(options["venditore"])
        # result = scrape_merchant_info(options["venditore"])
        # print(result)
        # if result['status'] == 'success':
#             self.stdout.write(self.style.SUCCESS(
#                 f"Successfully scraped merchant info\n"
#                 # f"File saved at: {result['file_path']}"
#             ))
#         else:
#             self.stdout.write(self.style.ERROR(
#                 f"Error: {result['message']}"
#             )) 