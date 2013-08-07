"""
Nose testing for JSON-LD spec for pyld
"""
import sys
import os
import json
import logging

from difflib import unified_diff
from urllib import urlretrieve
from zipfile import ZipFile

import nose

from pyld import jsonld

log = logging.getLogger(__name__)

# path foo
SPEC_URL = "https://codeload.github.com/json-ld/json-ld.org/zip/master"
BUILD_PATH = os.path.join(os.path.dirname(__file__), "..", "build")
SPEC_PATH = os.path.join(BUILD_PATH, "json-ld.org-master")
SUITE_PATH = os.path.join(SPEC_PATH, "test-suite", "tests")


def jld_expand(test, inp, options, test_dir):
    return jsonld.expand(input, options)


def jld_compact(test, inp, options, test_dir):
    with open(os.path.join(test_dir, test['context'])) as f:
        ctx = json.load(f)
    return jsonld.compact(inp, ctx, options)


def jld_flatten(test, inp, options, test_dir):
    return jsonld.flatten(inp, None, options)


def jld_frame(test, inp, options, test_dir):
    with open(os.path.join(test_dir, test['frame'])) as f:
        frame = json.load(f)
    return jsonld.frame(inp, frame, options)


def jld_from_rdf(test, inp, options, test_dir):
    return jsonld.from_rdf(inp, options)


def jld_to_rdf(test, inp, options, test_dir):
    options['format'] = 'application/nquads'
    return jsonld.to_rdf(inp, options)


def jld_normalize(test, inp, options, test_dir):
    options['format'] = 'application/nquads'
    return jsonld.normalize(inp, options)


# supported test types
TEST_TYPES = {
    "jld:ExpandTest": jld_expand,
    "jld:CompactTest": jld_compact,
    "jld:FlattenTest": jld_flatten,
    "jld:FrameTest": jld_frame,
    "jld:FromRDFTest": jld_from_rdf,
    "jld:ToRDFTest": jld_to_rdf,
    "jld:NormalizeTest": jld_normalize
}


SKIP_TEST_TYPES = ['jld:ApiErrorTest']


def test():
    if not os.path.exists(SPEC_PATH):
        zip_path, success = urlretrieve(SPEC_URL)
        if success:
            with ZipFile(zip_path, "r") as nav_zip:
                nav_zip.extractall(BUILD_PATH)
        else:
            raise Exception("Download of spec failed.")

    for bundle in load_tests():
        handler = get_handler(bundle["test"])

        def spec(manifest, spec):
            result = handler(
                bundle["test"],
                bundle["input"],
                bundle["options"],
                bundle["test_dir"]
            )

            result_str = cannonical(result)
            exp_str = cannonical(bundle["expect"])

            diff = list(unified_diff(
                exp_str, result_str, bundle["test"]["expect"], "result"
            ))

            log.debug("\n".join(diff))

            assert not diff

        yield (spec, bundle['manifest']['name'], bundle['test']['name'])


def cannonical(struct):
    if isinstance(struct, (list, dict)):
        return json.dumps(struct, sort_keys=True, indent=2).split("\n")
    return struct.split("\n")


def load_tests():
    "find all the spec files"
    for test_dir, dirs, files in os.walk(SUITE_PATH):
        for manifest in files:
            # add all .jsonld manifest files to the file list
            if "manifest" in manifest and is_jsonld(manifest):
                for test in parse_manifest(os.path.join(test_dir, manifest)):
                    yield test


def is_jsonld(path):
    return path.endswith(".jsonld")


def parse_manifest(manifest_file):
    test_dir = os.path.dirname(manifest_file)

    with open(manifest_file, "r") as f:
        manifest = json.load(f)

    for test in manifest["sequence"]:
        if doable(test):
            yield {
                "manifest": manifest,
                "test_dir": test_dir,
                "test": test,
                "options": base_options(test),
                "input": parse_input_expect(test_dir, test["input"]),
                "expect": parse_input_expect(test_dir, test["expect"]),
            }


def doable(test):
    return (
        set.intersection(set(TEST_TYPES), set(test["@type"]))
        and not set.intersection(set(SKIP_TEST_TYPES), set(test["@type"]))
    )


def parse_input_expect(test_dir, path):
    with open(os.path.join(test_dir, path)) as f:
        if is_jsonld(path):
            return json.load(f)
        return f.read().decode('utf8')


def base_options(test):
    # JSON-LD options
    return {
        "base": "http://json-ld.org/test-suite/tests/%s" % test["input"],
        "useNativeTypes": True
    }


def get_handler(test):
    for test_type in test["@type"]:
        if test_type in TEST_TYPES:
            return TEST_TYPES[test_type]
