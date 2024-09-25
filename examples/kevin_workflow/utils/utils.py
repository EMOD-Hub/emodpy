import os


def load_dropbox_path(user_path=None):

    """ Provide a single point of entry for user-, platform-, or machine-specific Dropbox installations """

    if not user_path:

        if os.environ['USERNAME'] == 'kmccarthy':

            if os.environ['COMPUTERNAME'] == 'IDMPPTSS03':
                user_path = os.path.join('D:', os.sep, 'kmccarthy')

            if os.environ['COMPUTERNAME'] == 'IDMPPWKS097':
                user_path = os.path.join('C:', os.sep, 'Users', 'kmccarthy')

        else: #Add more users here
            dropbox_path = None

    dropbox_path = os.path.join(user_path, 'Dropbox (IDM)', 'shchen')

    return dropbox_path


def load_output_path():
    base_path = load_dropbox_path(user_path=r'C:\Users\shchen')
    return os.path.join(base_path,  'KM-2020-polio-cVDPV2', 'outputs')


def load_input_path():
    base_path = load_dropbox_path(user_path=r'C:\Users\shchen')
    #return os.path.join(base_path, 'Measles Team Folder','Projects', 'KM-2020-polio-cVDPV2', 'inputs')
    return os.path.join(base_path, 'KM-2020-polio-cVDPV2', 'inputs')


def load_data_path():
    base_path = load_dropbox_path(user_path=r'C:\Users\shchen')
    return os.path.join(base_path, 'Measles Team Folder', 'Data')


def load_private_path():
    base_path = load_dropbox_path(user_path=r'C:\Users\shchen')
    return os.path.join(base_path, 'kmccarthy', 'KM-2020-polio-cVDPV2')