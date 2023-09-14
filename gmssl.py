# Copyright 2023 The GmSSL Project. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the License); you may
# not use this file except in compliance with the License.
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# pyGmSSL - the Python binding of the GmSSL library


from ctypes import *
from ctypes.util import find_library

libgmssl = find_library("gmssl")

gmssl = cdll.LoadLibrary(libgmssl)
libc = cdll.LoadLibrary(find_library('c'))


GMSSL_PYTHON_VERSION = "2.0"


def gmssl_version_num():
	return gmssl.gmssl_version_num()


def gmssl_version_str():
	gmssl.gmssl_version_str.restype = c_char_p
	p = gmssl.gmssl_version_str()
	return p.decode('ascii')

GMSSL_LIBRARY_VERSION = gmssl_version_str()


def rand_bytes(size):
	buf = create_string_buffer(size)
	gmssl.rand_bytes(buf, c_size_t(size))
	return buf.raw


class InnerError(Exception):
	'''
	GmSSL libraray inner error
	'''

SM3_DIGEST_SIZE = 32

class Sm3(Structure):

	SM3_STATE_WORDS = 8
	SM3_BLOCK_SIZE = 64

	_fields_ = [
		("dgst", c_uint32 * SM3_STATE_WORDS),
		("nblocks", c_uint64),
		("block", c_uint8 * SM3_BLOCK_SIZE),
		("num", c_size_t)
	]

	def __init__(self):
		gmssl.sm3_init(byref(self))

	def reset(self):
		gmssl.sm3_init(byref(self))

	def update(self, data):
		gmssl.sm3_update(byref(self), data, c_size_t(len(data)))

	def digest(self):
		dgst = create_string_buffer(SM3_DIGEST_SIZE)
		gmssl.sm3_finish(byref(self), dgst)
		return dgst.raw


SM3_HMAC_SIZE = SM3_DIGEST_SIZE
SM3_HMAC_MIN_KEY_SIZE = 16
SM3_HMAC_MAX_KEY_SIZE = 64

class Sm3Hmac(Structure):

	_fields_ = [
		("sm3_ctx", Sm3),
		("key", c_uint8 * Sm3.SM3_BLOCK_SIZE)
	]

	def __init__(self, key):
		if len(key) < SM3_HMAC_MIN_KEY_SIZE or len(key) > SM3_HMAC_MAX_KEY_SIZE:
			raise ValueError('Invalid SM3 HMAC key length')
		gmssl.sm3_hmac_init(byref(self), key, c_size_t(len(key)))

	def reset(self, key):
		if len(key) < SM3_HMAC_MIN_KEY_SIZE or len(key) > SM3_HMAC_MAX_KEY_SIZE:
			raise ValueError('Invalid SM3 HMAC key length')
		gmssl.sm3_hmac_init(byref(self), key, c_size_t(len(key)))

	def update(self, data):
		gmssl.sm3_hmac_update(byref(self), data, c_size_t(len(data)))

	def generateMac(self):
		hmac = create_string_buffer(SM3_HMAC_SIZE)
		gmssl.sm3_hmac_finish(byref(self), hmac)
		return hmac.raw


SM4_KEY_SIZE = 16
SM4_BLOCK_SIZE = 16



class Sm4(Structure):

	SM4_NUM_ROUNDS = 32

	_fields_ = [("rk", c_uint32 * SM4_NUM_ROUNDS)]

	def __init__(self, key, encrypt):
		if len(key) != SM4_KEY_SIZE:
			raise ValueError('Invalid key length')
		if encrypt:
			gmssl.sm4_set_encrypt_key(byref(self), key)
		else:
			gmssl.sm4_set_decrypt_key(byref(self), key)

	def encrypt(self, block):
		if len(block) != SM4_BLOCK_SIZE:
			raise ValueError('Invalid block size')
		outbuf = create_string_buffer(SM4_BLOCK_SIZE)
		gmssl.sm4_encrypt(byref(self), block, outbuf)
		return outbuf.raw


class Sm4Cbc(Structure):

	_fields_ = [
		("sm4_key", Sm4),
		("iv", c_uint8 * SM4_BLOCK_SIZE),
		("block", c_uint8 * SM4_BLOCK_SIZE),
		("block_nbytes", c_size_t)
	]

	def __init__(self, key, iv, encrypt):
		if len(key) != SM4_KEY_SIZE:
			raise ValueError('Invalid key length')
		if len(iv) != SM4_BLOCK_SIZE:
			raise ValueError('Invalid IV size')
		if encrypt == True:
			self._encrypt = True
			if gmssl.sm4_cbc_encrypt_init(byref(self), key, iv) != 1:
				raise InnerError('libgmssl inner error')
		else:
			self._encrypt = False
			if gmssl.sm4_cbc_decrypt_init(byref(self), key, iv) != 1:
				raise InnerError('libgmssl inner error')

	def update(self, data):
		outbuf = create_string_buffer(len(data) + SM4_BLOCK_SIZE)
		outlen = c_size_t()
		if self._encrypt == True:
			if gmssl.sm4_cbc_encrypt_update(byref(self), data, c_size_t(len(data)), outbuf, byref(outlen)) != 1:
				raise InnerError('libgmssl inner error')
		else:
			if gmssl.sm4_cbc_decrypt_update(byref(self), data, c_size_t(len(data)), outbuf, byref(outlen)) != 1:
				raise InnerError('libgmssl inner error')
		return outbuf[0:outlen.value]

	def finish(self):
		outbuf = create_string_buffer(SM4_BLOCK_SIZE)
		outlen = c_size_t()
		if self._encrypt == True:
			if gmssl.sm4_cbc_encrypt_finish(byref(self), outbuf, byref(outlen)) != 1:
				raise InnerError('libgmssl inner error')
		else:
			if gmssl.sm4_cbc_decrypt_finish(byref(self), outbuf, byref(outlen)) != 1:
				raise InnerError('libgmssl inner error')
		return outbuf[:outlen.value]



SM4_CTR_IV_SIZE = 16


class Sm4Ctr(Structure):

	_fields_ = [
		("sm4_key", Sm4),
		("ctr", c_uint8 * SM4_BLOCK_SIZE),
		("block", c_uint8 * SM4_BLOCK_SIZE),
		("block_nbytes", c_size_t)
	]

	def __init__(self, key, iv):
		if len(key) != SM4_KEY_SIZE:
			raise ValueError('Invalid key length')
		if len(iv) != SM4_BLOCK_SIZE:
			raise ValueError('Invalid IV size')
		if gmssl.sm4_ctr_encrypt_init(byref(self), key, iv) != 1:
			raise InnerError('libgmssl inner error')

	def update(self, data):
		outbuf = create_string_buffer(len(data) + SM4_BLOCK_SIZE)
		outlen = c_size_t()
		if gmssl.sm4_ctr_encrypt_update(byref(self), data, c_size_t(len(data)), outbuf, byref(outlen)) != 1:
			raise InnerError('libgmssl inner error')
		return outbuf[0:outlen.value]

	def finish(self):
		outbuf = create_string_buffer(SM4_BLOCK_SIZE)
		outlen = c_size_t()
		if gmssl.sm4_ctr_encrypt_finish(byref(self), outbuf, byref(outlen)) != 1:
			raise InnerError('libgmssl inner error')
		return outbuf[:outlen.value]


ZUC_KEY_SIZE = 16
ZUC_IV_SIZE = 16

class ZucState(Structure):
	_fields_ = [
		("LFSR", c_uint32 * 16),
		("R1", c_uint32),
		("R2", c_uint32)
	]

class Zuc(Structure):

	_fields_ = [
		("zuc_state", ZucState),
		("block", c_uint8 * 4),
		("block_nbytes", c_size_t)
	]

	def __init__(self, key, iv):
		if len(key) != ZUC_KEY_SIZE:
			raise ValueError('Invalid key length')
		if len(iv) != ZUC_IV_SIZE:
			raise ValueError('Invalid IV size')
		if gmssl.zuc_encrypt_init(byref(self), key, iv) != 1:
			raise InnerError('libgmssl inner error')

	def update(self, data):
		outbuf = create_string_buffer(len(data) + SM4_BLOCK_SIZE)
		outlen = c_size_t()
		if gmssl.zuc_encrypt_update(byref(self), data, c_size_t(len(data)), outbuf, byref(outlen)) != 1:
			raise InnerError('libgmssl inner error')
		return outbuf[0:outlen.value]

	def finish(self):
		outbuf = create_string_buffer(SM4_BLOCK_SIZE)
		outlen = c_size_t()
		if gmssl.zuc_encrypt_finish(byref(self), outbuf, byref(outlen)) != 1:
			raise InnerError('libgmssl inner error')
		return outbuf[:outlen.value]


class gf128_t(Structure):
	_fields_ = [
		("hi", c_uint64),
		("lo", c_uint64)
	]


class Ghash(Structure):
	_fields_ = [
		("H", gf128_t),
		("X", gf128_t),
		("aadlen", c_size_t),
		("clen", c_size_t),
		("block", c_uint8 * 16),
		("num", c_size_t)
	]


SM4_GCM_MIN_IV_SIZE = 1
SM4_GCM_MAX_IV_SIZE = 64
SM4_GCM_DEFAULT_IV_SIZE = 12
SM4_GCM_DEFAULT_TAG_SIZE = 16
SM4_GCM_MAX_TAG_SIZE = 16

class Sm4Gcm(Structure):

	_fields_ = [
		("sm4_ctr_ctx", Sm4Ctr),
		("mac_ctx", Ghash),
		("Y", c_uint8 * 16),
		("taglen", c_size_t),
		("mac", c_uint8 * 16),
		("maclen", c_size_t)
	]

	def __init__(self, key, iv, aad, taglen, encrypt):
		if len(key) != SM4_KEY_SIZE:
			raise ValueError('Invalid key length')
		if len(iv) < SM4_GCM_MIN_IV_SIZE or len(iv) > SM4_GCM_MAX_IV_SIZE:
			raise ValueError('Invalid IV size')
		if taglen < 1 or taglen > SM4_GCM_MAX_TAG_SIZE:
			raise ValueError('Invalid Tag length')
		if encrypt == True:
			ok = gmssl.sm4_gcm_encrypt_init(byref(self), key, c_size_t(len(key)),
				iv, c_size_t(len(iv)), aad, c_size_t(len(aad)), c_size_t(taglen))
		else:
			ok = gmssl.sm4_gcm_decrypt_init(byref(self), key, c_size_t(len(key)),
				iv, c_size_t(len(iv)), aad, c_size_t(len(aad)), c_size_t(taglen))
		if ok != 1:
			raise InnerError('libgmssl inner error')
		self._encrypt = encrypt


	def update(self, data):
		outbuf = create_string_buffer(len(data) + SM4_BLOCK_SIZE)
		outlen = c_size_t()
		if self._encrypt == True:
			if gmssl.sm4_gcm_encrypt_update(byref(self), data, c_size_t(len(data)), outbuf, byref(outlen)) != 1:
				raise InnerError('libgmssl inner error')
		else:
			if gmssl.sm4_gcm_decrypt_update(byref(self), data, c_size_t(len(data)), outbuf, byref(outlen)) != 1:
				raise InnerError('libgmssl inner error')
		return outbuf[0:outlen.value]

	def finish(self):
		outbuf = create_string_buffer(SM4_BLOCK_SIZE + SM4_GCM_MAX_TAG_SIZE)
		outlen = c_size_t()
		if self._encrypt == True:
			if gmssl.sm4_gcm_encrypt_finish(byref(self), outbuf, byref(outlen)) != 1:
				raise InnerError('libgmssl inner error')
		else:
			if gmssl.sm4_gcm_decrypt_finish(byref(self), outbuf, byref(outlen)) != 1:
				raise InnerError('libgmssl inner error')
		return outbuf[:outlen.value]


SM2_DEFAULT_ID = b'1234567812345678'

SM2_MAX_SIGNATURE_SIZE = 72
SM2_MIN_PLAINTEXT_SIZE = 1
SM2_MAX_PLAINTEXT_SIZE = 255
SM2_MIN_CIPHERTEXT_SIZE = 45
SM2_MAX_CIPHERTEXT_SIZE = 366


class Sm2Point(Structure):
	_fields_ = [
		("x", c_uint8 * 32),
		("y", c_uint8 * 32)
	]


class Sm2Key(Structure):

	_fields_ = [
		("public_key", Sm2Point),
		("private_key", c_uint8 * 32)
	]

	def generate_key(self):
		if gmssl.sm2_key_generate(byref(self)) != 1:
			raise InnerError('libgmssl inner error')

	def compute_z(self, signer_id):
		z = create_string_buffer(SM3_DIGEST_SIZE)
		gmssl.sm2_compute_z(z, byref(self), signer_id, c_size_t(len(signer_id)))
		return z.raw

	def export_encrypted_private_key_info_pem(self, file, passwd):
		libc.fopen.restype = c_void_p
		fp = libc.fopen(file.encode('utf-8'), 'wb')
		if gmssl.sm2_private_key_info_encrypt_to_pem(byref(self),
			passwd.encode('utf-8'), c_void_p(fp)) != 1:
			raise InnerError('libgmssl inner error')
		libc.fclose(c_void_p(fp))
		return True

	def import_encrypted_private_key_info_pem(self, file, passwd):
		libc.fopen.restype = c_void_p
		fp = libc.fopen(file.encode('utf-8'), 'rb')
		if gmssl.sm2_private_key_info_decrypt_from_pem(byref(self), passwd.encode('utf-8'), c_void_p(fp)) != 1:
			raise InnerError('libgmssl inner error')
		libc.fclose(c_void_p(fp))
		return True

	def export_public_key_info_pem(self, file):
		libc.fopen.restype = c_void_p
		fp = libc.fopen(file.encode('utf-8'), 'wb')
		if gmssl.sm2_public_key_info_to_pem(byref(self), c_void_p(fp)) != 1:
			raise InnerError('libgmssl inner error')
		libc.fclose(c_void_p(fp))
		return True

	def import_public_key_info_pem(self, file):
		libc.fopen.restype = c_void_p
		fp = libc.fopen(file.encode('utf-8'), 'rb')
		if gmssl.sm2_public_key_info_from_pem(byref(self), c_void_p(fp)) != 1:
			raise InnerError('libgmssl inner error')
		libc.fclose(c_void_p(fp))
		return True

	def sign(self, dgst):
		if len(dgst) != SM3_DIGEST_SIZE:
			raise ValueError('Invalid SM3 digest size')
		sig = create_string_buffer(SM2_MAX_SIGNATURE_SIZE)
		siglen = c_size_t()
		if gmssl.sm2_sign(byref(self), dgst, sig, byref(siglen)) != 1:
			raise InnerError('libgmssl inner error')
		return sig[:siglen.value]

	def verify(self, dgst, sig):
		if len(dgst) != SM3_DIGEST_SIZE:
			raise ValueError('Invalid SM3 digest size')
		ret = gmssl.sm2_verify(byref(self), dgst, sig, c_size_t(len(sig)))
		if ret < 0:
			raise InnerError('libgmssl inner error')
		if ret == 0:
			return False
		return True

	def encrypt(self, data):
		outbuf = create_string_buffer(SM2_MAX_CIPHERTEXT_SIZE)
		outlen = c_size_t()
		if gmssl.sm2_encrypt(byref(self), data, c_size_t(len(data)), outbuf, byref(outlen)) != 1:
			raise InnerError('libgmssl inner error')
		return outbuf[:outlen.value]

	def decrypt(self, ciphertext):
		outbuf = create_string_buffer(SM2_MAX_PLAINTEXT_SIZE)
		outlen = c_size_t()
		if gmssl.sm2_decrypt(byref(self), ciphertext, c_size_t(len(ciphertext)), outbuf, byref(outlen)) != 1:
			raise InnerError('libgmssl inner error')
		return outbuf[:outlen.value]


class Sm2Signature(Structure):

	_fields_ = [
		("sm3_ctx", Sm3),
		("key", Sm2Key)
	]

	def __init__(self, sm2_key, signer_id, sign):
		if sign == True:
			self._sign = True
			if gmssl.sm2_sign_init(byref(self), byref(sm2_key), signer_id, c_size_t(len(signer_id))) != 1:
				raise InnerError('libgmssl inner error')
		else:
			self._sign = False
			if gmssl.sm2_verify_init(byref(self), byref(sm2_key), signer_id, c_size_t(len(signer_id))) != 1:
				raise InnerError('libgmssl inner error')


	def update(self, data):
		if self._sign == True:
			if gmssl.sm2_sign_update(byref(self), data, c_size_t(len(data))) != 1:
				raise InnerError('libgmssl inner error')
		else:
			if gmssl.sm2_verify_update(byref(self), data, c_size_t(len(data))) != 1:
				raise InnerError('libgmssl inner error')

	def sign(self):
		sig = create_string_buffer(SM2_MAX_SIGNATURE_SIZE)
		siglen = c_size_t()
		if gmssl.sm2_sign_finish(byref(self), sig, byref(siglen)) != 1:
			raise InnerError('libgmssl inner error')
		return sig[:siglen.value]

	def verify(self, sig):
		ret = gmssl.sm2_verify_finish(byref(self), sig, c_size_t(len(sig)))
		if ret < 0:
			raise InnerError('libgmssl inner error')
		if ret == 0:
			return False
		return True










