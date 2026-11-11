"""Input-boundary tests only; real Docker acceptance has a separate driver."""
import unittest
from image_runtime import ImageFailure, validate_image_id, validate_probe


class ImageContracts(unittest.TestCase):
    def test_immutable_id(self):
        validate_image_id('sha256:' + 'a'*64)

    def test_tags_and_malformed_ids_rejected(self):
        for value in (None, '', 'python:latest', 'sha256:abc', 'sha256:'+'A'*64, {}, 1):
            with self.subTest(value=value), self.assertRaises(ImageFailure) as caught:
                validate_image_id(value)
            self.assertEqual(caught.exception.code, 'INVALID_IMAGE_ID')

    def test_probe_is_optional_and_bounded(self):
        validate_probe(None)
        validate_probe({'path':'/opt/m2-draft-marker-'+'a'*32, 'value':'a'*32})

    def test_probe_rejects_arbitrary_files_and_mismatched_tokens(self):
        for value in ({}, {'path':'/etc/passwd','value':'a'*32},
                      {'path':'/opt/m2-draft-marker-'+'a'*32,'value':'b'*32},
                      {'path':'/opt/m2-draft-marker-'+'a'*32,'value':'a'*32,'extra':True}):
            with self.subTest(value=value), self.assertRaises(ImageFailure) as caught:
                validate_probe(value)
            self.assertEqual(caught.exception.code,'INVALID_IMAGE_PROBE')


if __name__=='__main__':
    unittest.main()
