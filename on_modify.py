#!/usr/bin/env python3

###############################################################################
#
# Copyright 2016 - 2021, 2023, Gothenburg Bit Factory
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included
# in all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS
# OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL
# THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.
#
# https://www.opensource.org/licenses/mit-license.php
#
###############################################################################

import json
import subprocess
import sys

# Hook should extract all the following for use as Timewarrior tags:
#   UUID
#   Project
#   Tags
#   Description
#   UDAs

try:
    input_stream = sys.stdin.buffer
except AttributeError:
    input_stream = sys.stdin


# Extract attributes for use as tags.
def extract_tags(json_obj):
    tags = []
    if 'description' in json_obj:
        tags.append(json_obj['description'])
    if 'project' in json_obj:
        tags.append(json_obj['project'])
    if 'tags' in json_obj:
        tags.extend(json_obj['tags'])
    return tags


def extract_annotation(json_obj):
    if 'annotations' not in json_obj:
        return '\'\''

    return json_obj['annotations'][0]['description']


def extract_start(json_obj):
    return json_obj['start']


# Check if the active task matches the one in timewarrior, otherwsie exit
def check_tags(tags, action):
    active_tag_count = int(subprocess.run(['timew', 'get', 'dom.active.tag.count'], capture_output=True, text=True).stdout)
    match = True
    if len(tags) != active_tag_count:
        match = False
    else:
        for i in range(1, active_tag_count+1):
            if subprocess.run(['timew', 'get', 'dom.active.tag.' + str(i)], capture_output=True, text=True).stdout[:-1] not in tags:
                match = False
    if not match:
        print('Active timewarrior tags do not match modified task - Aborting ' + action)
        sys.exit(0)


def main(old, new):
    new_tags = extract_tags(new)
    old_tags = extract_tags(old)
    if 'start' in new:
        start = extract_start(new)

        # Started task.
        if 'start' not in old:
            subprocess.call(['timew', 'start', start] + new_tags + [':yes', ':adjust'])

        # Task modified
        else:
            check_tags(old_tags, 'modify')

            if old_tags != new_tags:
                subprocess.call(['timew', 'untag', '@1'] + old_tags + [':yes'])
                subprocess.call(['timew', 'tag', '@1'] + new_tags + [':yes'])

            if start != extract_start(old):
                print('Updating Timewarrior start time to ' + start)
                subprocess.call(['timew', 'modify', 'start', '@1', start])

            old_annotation = extract_annotation(old)
            new_annotation = extract_annotation(new)
            if old_annotation != new_annotation:
                subprocess.call(['timew', 'annotate', '@1', new_annotation])

    # Stopped task.
    elif 'start' in old:
        check_tags(old_tags, 'stop')
        subprocess.call(['timew', 'stop'] + new_tags + [':yes'])


if __name__ == "__main__":
    old = json.loads(input_stream.readline().decode("utf-8", errors="replace"))
    new = json.loads(input_stream.readline().decode("utf-8", errors="replace"))
    print(json.dumps(new))
    main(old, new)
