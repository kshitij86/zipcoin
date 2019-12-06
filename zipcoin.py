# MODULE 2.

# Imports below.
import datetime
import hashlib
import json
from flask import Flask, jsonify, request
import requests
from uuid import uuid4
from urllib.parse import urlparse

# Build blockchain.
# self means refer to current object. 


class Blockchain:
    
    def __init__(self):
        # Give proof of work, and previous hash as values.
        # The genesis block should have no previous hash, so give a default value.
        # Genesis block is the first block, has no ancestors.
        # previous_hash has default value '0' because SHA256 only accepts encoded strings. """
        
        self.chain = []
        self.transactions = []
        # transactions created before create_block because the method should know where to look for the transactions.
        self.create_block(proof=1, previous_hash='0')
        self.nodes = set()

    def create_block(self, proof, previous_hash):
        # Anywhere strings are used, it is beacuse of formatting errors or module only uses encoded strings
        # As this is a generalized blockchain, anything can be included in a block. 
        block = {'index' : len(self.chain) + 1,
                 'timestamp': str(datetime.datetime.now()),
                 'proof': proof,
                 'previous_hash': previous_hash,
                 'transactions': self.transactions}
        # Empty the list as same transactions cannot live in two different blocks (?). 
        self.transactions = []
        
        self.chain.append(block)
        return block
        
    
    def get_previous_block(self):
        # Return last block of the chain.
        return self.chain[-1]
    
    def proof_of_work(self, previous_proof):
        # Proof of work is a number hard to find (so mining it is scarce) but easy to verify.
        # Previous proof is used to caclulate new proof.
        # Increment by one until right proof is found.
        # Apparently the more leading zeroes in the hash, the harder it is to solve.
        # So we keep things simple here.
        # All this maths is just to make the hash_operation challenging to find.
        # encode() returns b'str'.
        new_proof = 1
        check_proof = False
        while check_proof is False:
            hash_operation = hashlib.sha256(str(new_proof**2 - previous_proof**2).encode()).hexdigest()
            # Miner wins.
            if hash_operation[:4] == '0000':
                check_proof = True
            # Miner loses. Screw miner.
            else:
                new_proof += 1
        return new_proof

    def hash(self, block):
        # Encode block, but I really don't know what that is.
        encoded_block = json.dumps(block, sort_keys=True).encode()
        return hashlib.sha256(encoded_block).hexdigest()
    
    # Pretty self-explanatory. 
    def is_chain_valid(self, chain):
        previous_block = chain[0]
        block_index = 1
        while block_index < len(chain):
            block = chain[block_index]
            if block['previous_hash'] != self.hash:
                return False
            previous_proof = previous_block['proof']
            proof = block['proof']
            hash_operation = hashlib.sha256(str(proof**2 - previous_proof**2).encode()).hexdigest()
            if hash_operation[:4] != '0000':
                return False
            previous_block = block
            block_index += 1
        return True

    # Add the transactions in a proper format.
    # Transactions taken care of.
    def add_transactions(self, sender, receiver, amount):
        self.transactions.append({'sender' : sender,
                                  'receiver' : receiver,
                                  'amount' : amount})
        # Get the last block.
        previous_block = self.get_previous_block()
        # Return the last block.
        return previous_block['index'] + 1

    # Add a new node to our 'self.nodes' set.
    def add_node(self, address):
        parsed_url = urlparse(address)
        # netloc is the 'url' in the parsed_url returned (http://localhost:5000/).
        self.nodes.add(parsed_url.netloc)

    # Replace chain with the longest one each time, to maintain consensus.
    def replace_chain(self):
        network = self.nodes
        longest_chain = None
        max_length = len(self.chain)
        # Get the chain length from the response object, to compare for longest chain.
        for node in network:
            response = requests.get(f'http://{node}/get_chain')
            if response.status_code == 200:
                length = response.json()['length']
                chain = response.json()
                if length > max_length and self.is_chain_valid(chain):
                    max_length = length
                    longest_chain = chain
        if longest_chain:
            self.chain = longest_chain
            return True
        else:
            return False


app = Flask(__name__)
# Mining the blockchain.

# Creating a port for the node on Port 5000.
# The UUID creates a random but unique key.
# Also remove the dashes.
node_address = str(uuid4()).replace('-', '')


# Blockchain object. 
blockchain = Blockchain()


# 200 response just means it's all fine.
@app.route("/mine_block", methods=["GET"])
def mine_block():
    previous_block = blockchain.get_previous_block()
    previous_proof = previous_block['proof']
    proof = blockchain.proof_of_work(previous_proof)
    previous_hash = blockchain.hash(previous_block)
    blockchain.add_transactions(sender=node_address, receiver='Anonymous', amount=1)
    block = blockchain.create_block(proof, previous_hash)
    # The response now has transactions also.
    response = {'message': 'Block mined.',
                 'index': block['index'],
                 'timestamp': block['timestamp'],
                 'proof': block['proof'],
                 'previous_hash' : block['previous_hash'],
                'transaction': block['transactions']}
    return jsonify(response), 200


@app.route("/get_chain", methods=["GET"])
def get_chain():
    response = {'chain' : blockchain.chain,
                'length' : len(blockchain.chain)}
    return jsonify(response), 200


# Check if the chain is valid.
@app.route("/is_valid", methods=["GET"])
def is_valid():
    is_valid = blockchain.is_chain_valid(blockchain.chain)
    if is_valid:
        response = {'message' : "This chain is VALID."}
    else:
        response = {"INVALID"}
    return jsonify(response), 200


# Add the transaction to the Blockchain.
"""
Basically,  this method takes transaction details from the file 
generated in Postman to add the transaction to the block,is my guess.
"""
# '201' code because we use POST request.
@app.route('/add_transaction', methods=["POST"])
def add_transaction():
    json = request.get_json()
    transaction_keys = ['sender', 'receiver', 'amount']
    if not all (key in json for key in transaction_keys):
        return 'Some elements of this transaction are MISSING.', 400
    index = blockchain.add_transactions(json['sender'], json['receiver'], json['amount'])
    response = {"message": f"This transaction will be added to block {index}"}
    return jsonify(response), 201


# Decentralizing the blockchain.
@app.route("/connect_node", methods=["POST"])
def connect_node():
    json = request.get_json()
    # This nodes returns a bunch of addresses where we want send our coins.
    nodes = json.get('nodes')
    if nodes is None:
        return "No Node", 400
    for node in nodes:
        blockchain.add_node(node)
    response = {'message': 'All nodes now CONNECTED',
                'total_nodes': list(blockchain.nodes)}
    return jsonify(response), 201

# Next we gotta replace the chains to maintain consensus.
# Also make other files to simulate connected users to different ports.




app.run(host='0.0.0.0', port=5000)