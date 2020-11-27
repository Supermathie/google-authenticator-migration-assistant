#!/usr/bin/env python3

import base64
import itertools
import sys
import urllib

import pygame
import qrcode
import qrcode.image.pil

from google_auth_pb2 import MigrationPayload
from surface_factory import SurfaceFactory

# magic numbers
qr_box_size = 10
fontsize = 24
background_colour = (0xe0, 0xe0, 0xe0)
text_colour = (0x00, 0x00, 0x00)
num_lines = 4
qr_border = 20

# init pygame
pygame.display.init()
pygame.font.init()

font = pygame.font.SysFont(pygame.font.get_default_font(), size=fontsize)
pygame.display.set_caption('Google Authenticator Migration Assistant') 

def display_qr_and_text(qrdata, textdata=()):
  if qrdata is None:
    qr_img = pygame.surface.Surface((500,0))
  else:
    qr = qrcode.QRCode(box_size=qr_box_size)
    qr.add_data(qrdata)
    qr_img = qr.make_image(image_factory=SurfaceFactory).surface()
  qr_img_size = qr_img.get_size()
  
  window = pygame.display.set_mode((qr_img_size[0] + qr_border, qr_img_size[1] + qr_border + font.get_height() * num_lines))
  window.fill(background_colour)
  window.blit(qr_img, (qr_border/2, qr_border/2))

  for (i, text) in enumerate(textdata):
    text = font.render(text, True, text_colour, background_colour)
    window.blit(text, (font.get_height()/2, qr_img_size[1] + qr_border + font.get_height() * i))

  pygame.display.update()

def generate_otp_urls_from_auth_string(otp_auth_string):
  if otp_auth_string.startswith('QR-Code:'):
    otp_auth_string = otp_auth_string[8:]
  
  url = urllib.parse.urlparse(otp_auth_string)
  if url.scheme != 'otpauth-migration':
    raise ValueError("unhandled scheme: {}" % url.scheme)

  data = urllib.parse.parse_qs(url.query)['data'][0]
  migration_payload = MigrationPayload.FromString(base64.decodebytes(data.encode()))
  otp_payloads = migration_payload.otp_parameters
  for otp_payload in otp_payloads:
    yield otp_payload.name, urllib.parse.urlunparse((
      'otpauth',
      'totp',
      otp_payload.name,
      None,
      urllib.parse.urlencode({
        'secret': base64.b32encode(otp_payload.secret),
        'issuer': otp_payload.issuer,
      }),
      None,
    ))

if sys.stdin.isatty():
  print("Enter the data from the QR code(s) generated by the exporter, terminated by EOF:")

def gen_data_to_display():
  for line in sys.stdin:
    for data in generate_otp_urls_from_auth_string(line.strip()):
      yield data

lines = sys.stdin.readlines()

if len(lines) == 0:
  print("No input! Aborting...", file=sys.stderr)
  sys.exit(1)

data_to_display = itertools.chain(*(generate_otp_urls_from_auth_string(line.strip()) for line in lines))
display_qr_and_text(None, ('Ensure your screen is protected from view', '', 'Press SPACE to start'))

while True:
  event = pygame.event.wait()
  if event.type == pygame.KEYDOWN and event.key == pygame.K_SPACE:
    try:
      name, url = next(data_to_display)
      print("Account: {}".format(name))
      display_qr_and_text(url, (name, '', 'Press SPACE to continue, or ESC to quit'))
    except StopIteration:
      print('Complete!')
      pygame.event.post(pygame.event.Event(pygame.QUIT))

  if event.type == pygame.KEYDOWN and event.key in (pygame.K_ESCAPE, pygame.K_q):
    pygame.event.post(pygame.event.Event(pygame.QUIT))

  if event.type == pygame.QUIT:
    pygame.quit() 
    break