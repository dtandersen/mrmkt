import yaml


def read_config() -> dict:
    with open('config.yaml') as f:
        # use safe_load instead load
        config = yaml.safe_load(f)

    return config
