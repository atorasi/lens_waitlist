import re
import time
import json
import random

import requests
import tls_client
import pyuseragents
from web3 import Web3 
from eth_account.messages import encode_defunct
from imap_tools import MailBox

from config import SITEKEY, TWO_CAPTCHA_TOKEN, LINK_TO_CHANGE_PROXY_IP, PROXY, USE_PROXY, TEXT, END_TEXT, email_list, pk_list
from utils import script_exceptions, logger


class LensWaitlist():
    def __init__(self, email: str, passwd: str, privat: str) -> None:
        self.email = email
        self.password = passwd
        self.private_key = privat
        
        self.w3 = Web3(Web3.HTTPProvider('https://polygon.llamarpc.com'))
        self.account = self.w3.eth.account.from_key(self.private_key)
        self.address = self.account.address
        
        self.session = tls_client.Session(
            client_identifier=random.choice(
                [
                    "chrome_103",
                    "chrome_104",
                    "chrome_105",
                    "chrome_106",
                    "chrome_107",
                    "chrome_108",
                    "chrome109",
                    "Chrome110",
                    "chrome111",
                    "chrome112",
                    "firefox_102",
                    "firefox_104",
                    "firefox108",
                    "Firefox110",
                    "opera_89",
                    "opera_90",
                ]
            ),
            random_tls_extension_order=True
        )
        self.session.headers = {
            'authority': 'waitlist-server.lens.dev',
            'accept': 'application/json, text/plain, */*',
            'accept-language': 'ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7',
            'content-type': 'application/json',
            'origin': 'https://waitlist.lens.xyz',
            'referer': 'https://waitlist.lens.xyz/',
            'user-agent': pyuseragents.random(),
        }
        
        self.session.proxies.update({'http': PROXY})

    @staticmethod
    def change_proxy_ip():
        r = requests.get(LINK_TO_CHANGE_PROXY_IP)
        time.sleep(10)
            
    @staticmethod
    def get_datatime():
        from datetime import datetime
        updated_string = datetime.utcnow().isoformat()[:-3] + 'Z'
        
        return updated_string
    
    @staticmethod
    @script_exceptions
    def get_captcha_token() -> str:
        from twocaptcha import TwoCaptcha
        solver = TwoCaptcha(TWO_CAPTCHA_TOKEN)
        result = solver.turnstile(sitekey=SITEKEY, url='https://waitlist.lens.xyz/')
        logger.info(f"Captcha Solved")

        return result['code']
    
    @script_exceptions
    def get_signature(self, message_text: str) -> str | bool:
        json_data = {
            'token': self.get_captcha_token()
        }
        
        r = self.session.post(url='https://waitlist-server.lens.dev/verify/turnstile', json=json_data)

        if json.loads(r.text)['message'] == 'Token is now valid':
            message = encode_defunct(text=message_text)
            sign = self.w3.eth.account.sign_message(message, private_key=self.private_key)
            signature = self.w3.to_hex(sign.signature)
            
            return signature
        return False
            
    @script_exceptions
    def get_nonce(self) -> str:
        r = self.session.get('https://waitlist-server.lens.dev/auth/nonce')
        nonce = json.loads(r.text)['nonce']
        
        return nonce
    
    @script_exceptions
    def verify_account(self) -> str:
        nonce = self.get_nonce()
        datatime = self.get_datatime()
        message = f'waitlist.lens.xyz wants you to sign in with your Ethereum account:\n{self.address}\n\nSign in with Ethereum to the Lens Waitlist app.\n\nURI: https://waitlist.lens.xyz\nVersion: 1\nChain ID: 137\nNonce: {nonce}\nIssued At: {datatime}'
        
        json_data = {
            'message': message,
            'signature': self.get_signature(message_text=message),
            'nonce': nonce,
        }
        
        r = self.session.post(url='https://waitlist-server.lens.dev/auth/verify', json=json_data)
        token = json.loads(r.text)['token']
        logger.info(f'Received a token to connect to the site')

        return token
        
    @script_exceptions
    def submit_email_address(self) -> int:
        self.session.headers.update({'authorization': f'Bearer {self.verify_account()}'})
        
        json_data = {
            'email': self.email
        }
        
        r = self.session.post(url='https://waitlist-server.lens.dev/link/email', json=json_data)
        
        return r.status_code

    
    @script_exceptions
    def get_code_from_email(self) -> str | bool:
        time.sleep(5)
        with MailBox('outlook.office365.com').login(self.email, self.password) as mailbox:
            for _ in range(6):
                mailbox.folder.set('Junk')
                for msg in mailbox.fetch():
                    if '@lens.xyz'in str(msg.from_):
                        link = re.search(
                            r'[\s\S]+your\ eligibility\ notification![\s\S]+href="([\s\S]+?)"',
                            msg.html
                        ).group(1)
                        logger.info(f'Got the link to the Email verif.')
                        
                        return link
                    
                    else:   
                        time.sleep(3)
            return False
        
    @script_exceptions
    def email_verify(self) -> None:
        link = self.get_code_from_email()
        r = self.session.get(link)

        logger.info(f'Confirmed email: {self.email}')

        
    def fxkc_lens_wl(self) -> None:
        logger.info(f'Starting the account: {self.email}')
        self.submit_email_address()
        self.email_verify()
        logger.success(f'Finished the account : {self.email}')



if __name__ == '__main__':
    print(TEXT)
    time.sleep(7)
    
    logger.info(f'{len(email_list) if len(email_list) < len(pk_list) else len(pk_list)} accounts uploaded')
    
    for email_pass, private in zip(email_list, pk_list):
        mail = email_pass.split(':')
        
        if USE_PROXY: LensWaitlist.change_proxy_ip() 
        
        client = LensWaitlist(mail[0], mail[1], private)
        client.fxkc_lens_wl()
    
    print(END_TEXT)
    
        
    
    


