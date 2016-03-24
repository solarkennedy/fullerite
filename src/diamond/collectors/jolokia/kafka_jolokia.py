# -*- coding: utf-8 -*-

"""
Collect Kafka metrics using jolokia agent

### Example Configuration

```
    host = localhost
    port = 8778
```
"""

from jolokia import JolokiaCollector
import re

class KafkaJolokiaCollector(JolokiaCollector):
    TOTAL_TOPICS = re.compile('kafka\.server:name=.*PerSec,type=BrokerTopicMetrics')

    def collect_bean(self, prefix, obj):
        if isinstance(obj, dict) and "Count" in obj:
            counter_val = obj["Count"]
            self.parse_and_publish(prefix, "count", counter_val)
        else:
            for k, v in obj.iteritems():
                if type(v) in [int, float, long]:
                    self.parse_and_publish(prefix, k, v)
                elif isinstance(v, dict):
                    self.collect_bean("%s.%s" % (prefix, k), v)
                elif isinstance(v, list):
                    self.interpret_bean_with_list("%s.%s" % (prefix, k), v)

    def parse_and_publish(self, prefix, key, value):
        metric_prefix, meta = prefix.split(':', 1)
        name, metric_type, self.dimensions = self.parse_meta(meta)

        # If the prefix matches the TOTAL_TOPICS regular expression it means
        # that, metric has no topic associated with it and is really for all topics on that broker
        if re.match(self.TOTAL_TOPICS, prefix):
            self.dimensions["topic"] = "_TOTAL_"

        metric_name_list = [metric_prefix]
        if self.config.get('prefix', None):
            metric_name_list = [self.config['prefix'], metric_prefix]
        if metric_type:
            metric_name_list.append(metric_type)
        if name:
            metric_name_list.append(name)

        metric_name_list.append(key.lower())
        metric_name = '.'.join(metric_name_list)
        metric_name = self.clean_up(metric_name)
        if metric_name == "":
            self.dimensions = {}
            return

        if key.lower() == 'count':
            self.publish_cumulative_counter(metric_name, value)
        else:
            self.publish(metric_name, value)

    def parse_meta(self, meta):
        dimensions = {}
        for k, v in [kv.split('=') for kv in meta.split(',')]:
            dimensions[str(k)] = v

        metric_name = dimensions.pop("name", None)
        metric_type = dimensions.pop("type", None)
        return metric_name, metric_type, dimensions