import re
import pathlib
import warnings
import h5py
import numpy as np
from datetime import datetime
import warnings
from abc import ABC

from desc.backend import TextColors

def output_to_file(fname, equil):
    """Prints the equilibrium solution to a text file

    Parameters
    ----------
    fname : str or path-like
        filename of output file.
    equil : dict
        dictionary of equilibrium parameters.

    Returns
    -------

    """

    cR = equil['cR']
    cZ = equil['cZ']
    cL = equil['cL']
    bdryR = equil['bdryR']
    bdryZ = equil['bdryZ']
    cP = equil['cP']
    cI = equil['cI']
    Psi_lcfs = equil['Psi_lcfs']
    NFP = equil['NFP']
    zern_idx = equil['zern_idx']
    lambda_idx = equil['lambda_idx']
    bdry_idx = equil['bdry_idx']

    # open file
    file = open(fname, 'w+')
    file.seek(0)

    # scaling factors
    file.write('NFP = {:3d}\n'.format(NFP))
    file.write('Psi = {:16.8E}\n'.format(Psi_lcfs))

    # boundary paramters
    nbdry = len(bdry_idx)
    file.write('Nbdry = {:3d}\n'.format(nbdry))
    for k in range(nbdry):
        file.write('m: {:3d} n: {:3d} bR = {:16.8E} bZ = {:16.8E}\n'.format(
            int(bdry_idx[k, 0]), int(bdry_idx[k, 1]), bdryR[k], bdryZ[k]))

    # profile coefficients
    nprof = max(cP.size, cI.size)
    file.write('Nprof = {:3d}\n'.format(nprof))
    for k in range(nprof):
        if k >= cP.size:
            file.write(
                'l: {:3d} cP = {:16.8E} cI = {:16.8E}\n'.format(k, 0, cI[k]))
        elif k >= cI.size:
            file.write(
                'l: {:3d} cP = {:16.8E} cI = {:16.8E}\n'.format(k, cP[k], 0))
        else:
            file.write(
                'l: {:3d} cP = {:16.8E} cI = {:16.8E}\n'.format(k, cP[k], cI[k]))

    # R & Z Fourier-Zernike coefficients
    nRZ = len(zern_idx)
    file.write('NRZ = {:5d}\n'.format(nRZ))
    for k, lmn in enumerate(zern_idx):
        file.write('l: {:3d} m: {:3d} n: {:3d} cR = {:16.8E} cZ = {:16.8E}\n'.format(
            lmn[0], lmn[1], lmn[2], cR[k], cZ[k]))

    # lambda Fourier coefficients
    nL = len(lambda_idx)
    file.write('NL = {:5d}\n'.format(nL))
    for k, mn in enumerate(lambda_idx):
        file.write('m: {:3d} n: {:3d} cL = {:16.8E}\n'.format(
            mn[0], mn[1], cL[k]))

    # close file
    file.truncate()
    file.close()

    return None


def read_desc(filename):
    """reads a previously generated DESC ascii output file

    Parameters
    ----------
    filename : str or path-like
        path to file to read

    Returns
    -------
    equil : dict
        dictionary of equilibrium parameters.

    """

    equil = {}
    f = open(filename, 'r')
    lines = list(f)
    equil['NFP'] = int(lines[0].strip('\n').split()[-1])
    equil['Psi_lcfs'] = float(lines[1].strip('\n').split()[-1])
    lines = lines[2:]

    Nbdry = int(lines[0].strip('\n').split()[-1])
    equil['bdry_idx'] = np.zeros((Nbdry, 2), dtype=int)
    equil['bdryR'] = np.zeros(Nbdry)
    equil['bdryZ'] = np.zeros(Nbdry)
    for i in range(Nbdry):
        equil['bdry_idx'][i, 0] = int(lines[i+1].strip('\n').split()[1])
        equil['bdry_idx'][i, 1] = int(lines[i+1].strip('\n').split()[3])
        equil['bdryR'][i] = float(lines[i+1].strip('\n').split()[6])
        equil['bdryZ'][i] = float(lines[i+1].strip('\n').split()[9])
    lines = lines[Nbdry+1:]

    Nprof = int(lines[0].strip('\n').split()[-1])
    equil['cP'] = np.zeros(Nprof)
    equil['cI'] = np.zeros(Nprof)
    for i in range(Nprof):
        equil['cP'][i] = float(lines[i+1].strip('\n').split()[4])
        equil['cI'][i] = float(lines[i+1].strip('\n').split()[7])
    lines = lines[Nprof+1:]

    NRZ = int(lines[0].strip('\n').split()[-1])
    equil['zern_idx'] = np.zeros((NRZ, 3), dtype=int)
    equil['cR'] = np.zeros(NRZ)
    equil['cZ'] = np.zeros(NRZ)
    for i in range(NRZ):
        equil['zern_idx'][i, 0] = int(lines[i+1].strip('\n').split()[1])
        equil['zern_idx'][i, 1] = int(lines[i+1].strip('\n').split()[3])
        equil['zern_idx'][i, 2] = int(lines[i+1].strip('\n').split()[5])
        equil['cR'][i] = float(lines[i+1].strip('\n').split()[8])
        equil['cZ'][i] = float(lines[i+1].strip('\n').split()[11])
    lines = lines[NRZ+1:]

    NL = int(lines[0].strip('\n').split()[-1])
    equil['lambda_idx'] = np.zeros((NL, 2), dtype=int)
    equil['cL'] = np.zeros(NL)
    for i in range(NL):
        equil['lambda_idx'][i, 0] = int(lines[i+1].strip('\n').split()[1])
        equil['lambda_idx'][i, 1] = int(lines[i+1].strip('\n').split()[3])
        equil['cL'][i] = float(lines[i+1].strip('\n').split()[6])
    lines = lines[NL+1:]

    return equil

def reader_factory(load_from, file_format):
    if file_format == 'hdf5':
        reader = hdf5Reader(load_from)
    else:
        raise NotImplementedError("Format '{}' has not been implemented.".format(file_format))
    return reader

class hdf5Reader:
    def __init__(self, load_from):
        self.load_from = load_from
        self.resolve_base()

    def __del__(self):
        self.close()

    def check_hdf5_type(self, obj):
        if type(obj) is h5py._hl.group.Group or type(obj) is h5py._hl.files.File:
            return True
        else:
            return False

    def resolve_base(self):
        if self.check_hdf5_type(self.load_from):
            self.base = self.load_from
            self._close_base_ = False
        elif type(self.load_from) is str:
            self.base = h5py.File(self.load_from, 'r')
            self._close_base_ = True
        else:
            raise SyntaxError('save_to of type {} is not a filename or hdf5 '
                'file or group.'.format(type(self.load_from)))

    def resolve_where(self, where):
        if where is None:
            loc = self.base
        elif self.check_hdf5_type(where):
            loc = where
        else:
            raise SyntaxError("where '{}' is not a readable type. Must be "
                    "hdf5 file or group".format(where))
        return loc

    def read_obj(self, obj, where=None):
        loc = self.resolve_where(where)
        for attr in obj._save_attrs_:
            try:
                setattr(obj, attr, loc[attr][()])
            except KeyError:
                warnings.warn("Save attribute '{}' was not loaded.".format(attr),
                        RuntimeWarning)
        return None

    def read_dict(self, thedict, where=None):
        loc = self.resolve_where(where)
        for key in loc.keys():
            try:
                thedict.update({key : loc[key][()]})
            except AttributeError:
                # don't load subgroups
                pass
            #    warnings.warn("Save attribute '{}' was not loaded.".format(attr),
            #            RuntimeWarning)
        return None

    #def load_configuration(self, where=None):
    #    kwargs = {}
    #    self.read_dict(kwargs, where=where)
    #    return Configuration(**kwargs)

    #def load_equilibrium(self, where=None):
    #    kwargs = {}
    #    self.read_dict(self, where=None)
    #    eq = Equilibrium(**kwargs)

        # overwrite the configuration in constructor
    #    configuration_kwargs = {}
    #    eq.initial = self.load_configuration(configuration_kwargs,
    #            where=self.sub('initial'))
    #    return eq

    def sub(self, name):
        try:
            return self.base.create_group(name)
        except ValueError:
            return self.base[name]

    def groups(self, where):
        loc = self.resolve_where(where)
        return list(loc.keys())

    def close(self):
        if self._close_base_:
            self.base.close()
            self._close_base_ = False
        #else:
        #    warnings.warn('File cannot be closed in this scope.', RuntimeWarning)
        return None

def writer_factory(save_to, file_format, file_mode='w'):
    if file_format == 'hdf5':
        writer = hdf5Writer(save_to, file_mode)
    else:
        raise NotImplementedError("Format '{}' has not been implemented.".format(file_format))
    return writer

class hdf5Writer:
    def __init__(self, save_to, file_mode):
        self.save_to = save_to
        self.save_to_type = type(save_to)
        self.file_mode = file_mode
        self.resolve_base()

    def __del__(self):
        self.close()

    def check_hdf5_type(self, obj):
        if type(obj) is h5py._hl.group.Group or type(obj) is h5py._hl.files.File:
            return True
        else:
            return False

    def resolve_base(self):
        if self.check_hdf5_type(self.save_to):
            self.base = self.save_to
            self._close_base_ = False
        elif self.save_to_type is str:
            self.base = h5py.File(self.save_to, self.file_mode)
            self._close_base_ = True
        else:
            raise SyntaxError('save_to of type {} is not a filename or hdf5 '
                'file or group.'.format(self.save_to_type))

    def resolve_where(self, where):
        if where is None:
            loc = self.base
        elif self.check_hdf5_type(where):
            loc = where
        else:
            raise SyntaxError("where '{}' is not a writable type. Must be "
                    "hdf5 file or group".format(where))
        return loc

    def write_obj(self, obj, where=None):
        loc = self.resolve_where(where)
        for attr in obj._save_attrs_:
            try:
                loc.create_dataset(attr, data=getattr(obj, attr))
            except AttributeError:
                warnings.warn("Save attribute '{}' was not saved as it does "
                        "not exist.".format(attr), RuntimeWarning)
        return None

    def write_dict(self, thedict, where=None):
        loc = self.resolve_where(where)
        for key in thedict.keys():
            loc.create_dataset(key, data=thedict[key])
        return None

    def sub(self, name):
        return self.base.create_group(name)

    def groups(self, where):
        loc = self.resolve_where(where)
        return list(loc.keys())



    def close(self):
        if self._close_base_:
            self.base.close()
            self._close_base_ = False
        #else:
        #    warnings.warn('File cannot be closed in this scope.', RuntimeWarning)
        return None

def subgroup(name, save_to, fmt):
    if fmt == 'hdf5':
        group = subgroup_hdf5(name, save_to)
    else:
        raise NotImplementedError("Format '{}' has not been implemented.".format(fmt))
    return group

def base_hdf5(save_to):
    save_to_type = type(save_to)
    if save_to_type is h5py._hl.group.Group or save_to_type is h5py._hl.files.File:
        group = save_to.create_group(name)
    else:
        raise SyntaxError('save_to must be an hdf5 file or group.')
    return group

def subgroup_hdf5(name, save_to):
    save_to_type = type(save_to)
    if save_to_type is h5py._hl.group.Group or save_to_type is h5py._hl.files.File:
        group = save_to.create_group(name)
    else:
        raise SyntaxError('save_to must be an hdf5 file or group.')
    return group

def save(obj, save_to, fmt='hdf5', file_mode='w'):
    if fmt == 'hdf5':
        write_hdf5(obj, save_to, file_mode=file_mode)
    else:
        raise NotImplementedError("Format '{}' has not been implemented.".format(fmt))
    return None

def write_hdf5(obj, save_to, file_mode='w'):
    """Writes attributes of obj from obj._save_attrs_ list to an hdf5 file.

    Parameters
    __________
    obj: object to save
        must have _save_attrs_ list attribute. Otherwise AttributeError raised.
    save_loc : str or path-like; hdf5 file or group
        file or group to write to. If str or path-like, file is created. If
        hdf5 file or group instance, datasets are created there.
    file_mode='w': str
        hdf5 file mode. Default is 'w'.
    """
    # check save_loc is an accepted type
    save_to_type = type(save_to)
    if save_to_type is h5py._hl.group.Group or save_to_type is h5py._hl.files.File:
        file_group = save_to
        close = False
    elif save_to_type is str:
        file_group = h5py.File(save_to, file_mode)
        close = True
    else:
        raise SyntaxError('save_to of type {} is not a filename or hdf5 '
            'file or group.'.format(save_to_type))

    # save to file or group
    for attr in obj._save_attrs_:
        file_group.create_dataset(attr, data=getattr(obj, attr))

    # close file if created
    if close:
        file_group.close()

    return None

def write_desc_h5(filename, equilibrium):
    """Writes a DESC equilibrium to a hdf5 format binary file

    Parameters
    ----------
    filename : str or path-like
        file to write to. If it doesn't exist,
        it is created.
    equilibrium : dict
        dictionary of equilibrium parameters.

    Returns
    -------

    """

    f = h5py.File(filename, 'w')
    equil = f.create_group('equilibrium')
    for key, val in equilibrium.items():
        equil.create_dataset(key, data=val)
    equil['zern_idx'].attrs.create('column_labels', ['l', 'm', 'n'])
    equil['bdry_idx'].attrs.create('column_labels', ['m', 'n'])
    equil['lambda_idx'].attrs.create('column_labels', ['m', 'n'])
    f.close()


class Checkpoint():
    """Class for periodically saving equilibria during solution

    Parameters
    ----------
    filename : str or path-like
        file to write to. If it does not exist,
        it will be created
    write_ascii : bool
        Whether to also write ascii files. By default,
        only an hdf5 file is created and appended with each new solution.
        If write_ascii is True, additional files will be written, each with
        the same base filename but appeneded with _0, _1,...

    Returns
    -------
    checkpointer: Checkpoint
        object with methods to periodically save solutions
    """

    def __init__(self, filename, write_ascii=False):

        self.filename = str(pathlib.Path(filename).resolve())
        if self.filename.endswith('.h5'):
            self.base_file = self.filename[:-3]
        elif self.filename.endswith('.hdf5'):
            self.base_file = self.filename[:-5]
        else:
            self.base_file = self.filename
            self.filename += '.h5'

        self.f = h5py.File(self.filename, 'w')
        _ = self.f.create_group('iterations')
        _ = self.f.create_group('final').create_group('equilibrium')
        self.write_ascii = write_ascii

    def write_iteration(self, equilibrium, iter_num, inputs=None, update_final=True):
        """Write an equilibrium to the checkpoint file

        Parameters
        ----------
        equilibrium : dict
            equilibrium to write
        iter_num : int
            iteration number
        inputs : dict, optional
             dictionary of input parameters to the solver (Default value = None)
        update_final : bool
            whether to update the 'final' equilibrium
            with this entry (Default value = True)

        Returns
        -------

        """
        iter_str = str(iter_num)
        if iter_str not in self.f['iterations']:
            self.f['iterations'].create_group(iter_str)
        if 'equilibrium' not in self.f['iterations'][iter_str]:
            self.f['iterations'][iter_str].create_group('equilibrium')
        for key, val in equilibrium.items():
            self.f['iterations'][iter_str]['equilibrium'][key] = val

        self.f['iterations'][iter_str]['equilibrium']['zern_idx'].attrs.create(
            'column_labels', ['l', 'm', 'n'])
        self.f['iterations'][iter_str]['equilibrium']['bdry_idx'].attrs.create(
            'column_labels', ['m', 'n'])
        self.f['iterations'][iter_str]['equilibrium']['lambda_idx'].attrs.create(
            'column_labels', ['m', 'n'])

        if self.write_ascii:
            fname = self.base_file + '_' + str(iter_str) + '.out'
            output_to_file(fname, equilibrium)

        if inputs is not None:
            arrays = ['Mpol', 'Ntor', 'Mnodes', 'Nnodes', 'bdry_ratio', 'pres_ratio',
                      'zeta_ratio', 'errr_ratio', 'pert_order', 'ftol', 'xtol', 'gtol', 'nfev']
            if 'inputs' not in self.f['iterations'][iter_str]:
                self.f['iterations'][iter_str].create_group('inputs')
            for key, val in inputs.items():
                if key in arrays and isinstance(iter_num, int):
                    val = val[iter_num-1]
                self.f['iterations'][iter_str]['inputs'][key] = val

        if update_final:
            if 'final' in self.f:
                del self.f['final']
            self.f['final'] = self.f['iterations'][iter_str]

    def close(self):
        """Close the checkpointing file"""
        self.f.close()


def vmec_to_desc_input(vmec_fname, desc_fname):
    """Converts a VMEC input file to an equivalent DESC input file

    Parameters
    ----------
    vmec_fname : str or path-like
        filename of VMEC input file
    desc_fname : str or path-like
        filename of DESC input file. If it already exists it is overwritten.

    Returns
    -------

    """

    # file objects
    vmec_file = open(vmec_fname, 'r')
    desc_file = open(desc_fname, 'w')

    desc_file.seek(0)
    now = datetime.now()
    date = now.strftime('%m/%d/%Y')
    time = now.strftime('%H:%M:%S')
    desc_file.write('# This DESC input file was auto generated from the VMEC input file\n# {}\n# on {} at {}.\n\n'
                    .format(vmec_fname, date, time))

    num_form = r'[-+]?\ *\d*\.?\d*(?:[Ee]\ *[-+]?\ *\d+)?'
    Ntor = 99

    pres_scale = 1.0
    cP = np.array([0.0])
    cI = np.array([0.0])
    axis = np.array([[0, 0, 0.0]])
    bdry = np.array([[0, 0, 0.0, 0.0]])

    for line in vmec_file:
        comment = line.find('!')
        command = (line.strip()+' ')[0:comment]

        # global parameters
        if re.search(r'LRFP\s*=\s*T', command, re.IGNORECASE):
            warnings.warn(
                TextColors.WARNING + 'Using poloidal flux instead of toroidal flux!' + TextColors.ENDC)
        match = re.search('LASYM\s*=\s*[TF]', command, re.IGNORECASE)
        if match:
            if re.search(r'T', match.group(0), re.IGNORECASE):
                desc_file.write('stell_sym \t=   0\n')
            else:
                desc_file.write('stell_sym \t=   1\n')
        match = re.search(r'NFP\s*=\s*'+num_form, command, re.IGNORECASE)
        if match:
            numbers = [int(x) for x in re.findall(
                num_form, match.group(0)) if re.search(r'\d', x)]
            desc_file.write('NFP\t\t\t= {:3d}\n'.format(numbers[0]))
        match = re.search(r'PHIEDGE\s*=\s*'+num_form, command, re.IGNORECASE)
        if match:
            numbers = [float(x) for x in re.findall(
                num_form, match.group(0)) if re.search(r'\d', x)]
            desc_file.write('Psi_lcfs\t= {:16.8E}\n'.format(numbers[0]))
        match = re.search(r'MPOL\s*=\s*'+num_form, command, re.IGNORECASE)
        if match:
            numbers = [int(x) for x in re.findall(
                num_form, match.group(0)) if re.search(r'\d', x)]
            desc_file.write('Mpol\t\t= {:3d}\n'.format(numbers[0]))
        match = re.search(r'NTOR\s*=\s*'+num_form, command, re.IGNORECASE)
        if match:
            numbers = [int(x) for x in re.findall(
                num_form, match.group(0)) if re.search(r'\d', x)]
            desc_file.write('Ntor\t\t= {:3d}\n'.format(numbers[0]))
            Ntor = numbers[0]

        # pressure profile
        match = re.search(r'bPMASS_TYPE\s*=\s*\w*', command, re.IGNORECASE)
        if match:
            if not re.search(r'\bpower_series\b', match.group(0), re.IGNORECASE):
                warnings.warn(
                    TextColors.WARNING + 'Pressure is not a power series!' + TextColors.ENDC)
        match = re.search(r'GAMMA\s*=\s*'+num_form, command, re.IGNORECASE)
        if match:
            numbers = [float(x) for x in re.findall(
                num_form, match.group(0)) if re.search(r'\d', x)]
            if numbers[0] != 0:
                warnings.warn(TextColors.WARNING +
                              'GAMMA is not 0.0' + TextColors.ENDC)
        match = re.search(r'BLOAT\s*=\s*'+num_form, command, re.IGNORECASE)
        if match:
            numbers = [float(x) for x in re.findall(
                num_form, match.group(0)) if re.search(r'\d', x)]
            if numbers[0] != 1:
                warnings.warn(TextColors.WARNING +
                              'BLOAT is not 1.0' + TextColors.ENDC)
        match = re.search(r'SPRES_PED\s*=\s*'+num_form, command, re.IGNORECASE)
        if match:
            numbers = [float(x) for x in re.findall(
                num_form, match.group(0)) if re.search(r'\d', x)]
            if numbers[0] != 1:
                warnings.warn(TextColors.WARNING +
                              'SPRES_PED is not 1.0' + TextColors.ENDC)
        match = re.search(r'PRES_SCALE\s*=\s*'+num_form,
                          command, re.IGNORECASE)
        if match:
            numbers = [float(x) for x in re.findall(
                num_form, match.group(0)) if re.search(r'\d', x)]
            pres_scale = numbers[0]
        match = re.search(r'AM\s*=(\s*'+num_form+')*', command, re.IGNORECASE)
        if match:
            numbers = [float(x) for x in re.findall(
                num_form, match.group(0)) if re.search(r'\d', x)]
            for k in range(len(numbers)):
                l = 2*k
                if cP.size < l+1:
                    cP = np.pad(cP, (0, l+1-cP.size), mode='constant')
                cP[l] = numbers[k]

        # rotational transform
        match = re.search(r'NCURR\s*=(\s*'+num_form+')*',
                          command, re.IGNORECASE)
        if match:
            numbers = [float(x) for x in re.findall(
                num_form, match.group(0)) if re.search(r'\d', x)]
            if numbers[0] != 0:
                warnings.warn(
                    TextColors.WARNING + 'Not using rotational transform!' + TextColors.ENDC)
        if re.search(r'\bPIOTA_TYPE\b', command, re.IGNORECASE):
            if not re.search(r'\bpower_series\b', command, re.IGNORECASE):
                warnings.warn(TextColors.WARNING +
                              'Iota is not a power series!' + TextColors.ENDC)
        match = re.search(r'AI\s*=(\s*'+num_form+')*', command, re.IGNORECASE)
        if match:
            numbers = [float(x) for x in re.findall(
                num_form, match.group(0)) if re.search(r'\d', x)]
            for k in range(len(numbers)):
                l = 2*k
                if cI.size < l+1:
                    cI = np.pad(cI, (0, l+1-cI.size), mode='constant')
                cI[l] = numbers[k]

        # magnetic axis
        match = re.search(r'RAXIS\s*=(\s*'+num_form+')*',
                          command, re.IGNORECASE)
        if match:
            numbers = [float(x) for x in re.findall(
                num_form, match.group(0)) if re.search(r'\d', x)]
            for k in range(len(numbers)):
                if k > Ntor:
                    l = -k+Ntor+1
                else:
                    l = k
                idx = np.where(axis[:, 0] == l)[0]
                if np.size(idx) > 0:
                    axis[idx[0], 1] = numbers[k]
                else:
                    axis = np.pad(axis, ((0, 1), (0, 0)), mode='constant')
                    axis[-1, :] = np.array([l, numbers[k], 0.0])
        match = re.search(r'ZAXIS\s*=(\s*'+num_form+')*',
                          command, re.IGNORECASE)
        if match:
            numbers = [float(x) for x in re.findall(
                num_form, match.group(0)) if re.search(r'\d', x)]
            for k in range(len(numbers)):
                if k > Ntor:
                    l = k-Ntor-1
                else:
                    l = -k
                idx = np.where(axis[:, 0] == l)[0]
                if np.size(idx) > 0:
                    axis[idx[0], 2] = numbers[k]
                else:
                    axis = np.pad(axis, ((0, 1), (0, 0)), mode='constant')
                    axis[-1, :] = np.array([l, 0.0, numbers[k]])

        # boundary shape
        # RBS*sin(m*t-n*p) = RBS*sin(m*t)*cos(n*p) - RBS*cos(m*t)*sin(n*p)
        match = re.search(r'RBS\(\s*'+num_form+'\s*,\s*'+num_form +
                          '\s*\)\s*=\s*'+num_form, command, re.IGNORECASE)
        if match:
            numbers = [float(x) for x in re.findall(
                num_form, match.group(0)) if re.search(r'\d', x)]
            n = int(numbers[0])
            m = int(numbers[1])
            n_sgn = np.sign(np.array([n]))[0]
            n *= n_sgn
            if np.sign(m) < 0:
                warnings.warn(TextColors.WARNING +
                              'm is negative!' + TextColors.ENDC)
            RBS = numbers[2]
            if m != 0:
                m_idx = np.where(bdry[:, 0] == -m)[0]
                n_idx = np.where(bdry[:, 1] == n)[0]
                idx = np.where(np.isin(m_idx, n_idx))[0]
                if np.size(idx) > 0:
                    bdry[m_idx[idx[0]], 2] = RBS
                else:
                    bdry = np.pad(bdry, ((0, 1), (0, 0)), mode='constant')
                    bdry[-1, :] = np.array([-m, n, RBS, 0.0])
            if n != 0:
                m_idx = np.where(bdry[:, 0] == m)[0]
                n_idx = np.where(bdry[:, 1] == -n)[0]
                idx = np.where(np.isin(m_idx, n_idx))[0]
                if np.size(idx) > 0:
                    bdry[m_idx[idx[0]], 2] = -n_sgn*RBS
                else:
                    bdry = np.pad(bdry, ((0, 1), (0, 0)), mode='constant')
                    bdry[-1, :] = np.array([m, -n, -n_sgn*RBS, 0.0])
        # RBC*cos(m*t-n*p) = RBC*cos(m*t)*cos(n*p) + RBC*sin(m*t)*sin(n*p)
        match = re.search(r'RBC\(\s*'+num_form+'\s*,\s*'+num_form +
                          '\s*\)\s*=\s*'+num_form, command, re.IGNORECASE)
        if match:
            numbers = [float(x) for x in re.findall(
                num_form, match.group(0)) if re.search(r'\d', x)]
            n = int(numbers[0])
            m = int(numbers[1])
            n_sgn = np.sign(np.array([n]))[0]
            n *= n_sgn
            if np.sign(m) < 0:
                warnings.warn(TextColors.WARNING +
                              'm is negative!' + TextColors.ENDC)
            RBC = numbers[2]
            m_idx = np.where(bdry[:, 0] == m)[0]
            n_idx = np.where(bdry[:, 1] == n)[0]
            idx = np.where(np.isin(m_idx, n_idx))[0]
            if np.size(idx) > 0:
                bdry[m_idx[idx[0]], 2] = RBC
            else:
                bdry = np.pad(bdry, ((0, 1), (0, 0)), mode='constant')
                bdry[-1, :] = np.array([m, n, RBC, 0.0])
            if m != 0 and n != 0:
                m_idx = np.where(bdry[:, 0] == -m)[0]
                n_idx = np.where(bdry[:, 1] == -n)[0]
                idx = np.where(np.isin(m_idx, n_idx))[0]
                if np.size(idx) > 0:
                    bdry[m_idx[idx[0]], 2] = n_sgn*RBC
                else:
                    bdry = np.pad(bdry, ((0, 1), (0, 0)), mode='constant')
                    bdry[-1, :] = np.array([-m, -n, n_sgn*RBC, 0.0])
        # ZBS*sin(m*t-n*p) = ZBS*sin(m*t)*cos(n*p) - ZBS*cos(m*t)*sin(n*p)
        match = re.search(r'ZBS\(\s*'+num_form+'\s*,\s*'+num_form +
                          '\s*\)\s*=\s*'+num_form, command, re.IGNORECASE)
        if match:
            numbers = [float(x) for x in re.findall(
                num_form, match.group(0)) if re.search(r'\d', x)]
            n = int(numbers[0])
            m = int(numbers[1])
            n_sgn = np.sign(np.array([n]))[0]
            n *= n_sgn
            if np.sign(m) < 0:
                warnings.warn(TextColors.WARNING +
                              'm is negative!' + TextColors.ENDC)
            ZBS = numbers[2]
            if m != 0:
                m_idx = np.where(bdry[:, 0] == -m)[0]
                n_idx = np.where(bdry[:, 1] == n)[0]
                idx = np.where(np.isin(m_idx, n_idx))[0]
                if np.size(idx) > 0:
                    bdry[m_idx[idx[0]], 3] = ZBS
                else:
                    bdry = np.pad(bdry, ((0, 1), (0, 0)), mode='constant')
                    bdry[-1, :] = np.array([-m, n, 0.0, ZBS])
            if n != 0:
                m_idx = np.where(bdry[:, 0] == m)[0]
                n_idx = np.where(bdry[:, 1] == -n)[0]
                idx = np.where(np.isin(m_idx, n_idx))[0]
                if np.size(idx) > 0:
                    bdry[m_idx[idx[0]], 3] = -n_sgn*ZBS
                else:
                    bdry = np.pad(bdry, ((0, 1), (0, 0)), mode='constant')
                    bdry[-1, :] = np.array([m, -n, 0.0, -n_sgn*ZBS])
        # ZBC*cos(m*t-n*p) = ZBC*cos(m*t)*cos(n*p) + ZBC*sin(m*t)*sin(n*p)
        match = re.search(r'ZBC\(\s*'+num_form+'\s*,\s*'+num_form +
                          '\s*\)\s*=\s*'+num_form, command, re.IGNORECASE)
        if match:
            numbers = [float(x) for x in re.findall(
                num_form, match.group(0)) if re.search(r'\d', x)]
            n = int(numbers[0])
            m = int(numbers[1])
            n_sgn = np.sign(np.array([n]))[0]
            n *= n_sgn
            if np.sign(m) < 0:
                warnings.warn(TextColors.WARNING +
                              'm is negative!' + TextColors.ENDC)
            ZBC = numbers[2]
            m_idx = np.where(bdry[:, 0] == m)[0]
            n_idx = np.where(bdry[:, 1] == n)[0]
            idx = np.where(np.isin(m_idx, n_idx))[0]
            if np.size(idx) > 0:
                bdry[m_idx[idx[0]], 3] = ZBC
            else:
                bdry = np.pad(bdry, ((0, 1), (0, 0)), mode='constant')
                bdry[-1, :] = np.array([m, n, 0.0, ZBC])
            if m != 0 and n != 0:
                m_idx = np.where(bdry[:, 0] == -m)[0]
                n_idx = np.where(bdry[:, 1] == -n)[0]
                idx = np.where(np.isin(m_idx, n_idx))[0]
                if np.size(idx) > 0:
                    bdry[m_idx[idx[0]], 3] = n_sgn*ZBC
                else:
                    bdry = np.pad(bdry, ((0, 1), (0, 0)), mode='constant')
                    bdry[-1, :] = np.array([-m, -n, 0.0, n_sgn*ZBC])

        # catch multi-line inputs
        match = re.search(r'=', command)
        if not match:
            numbers = [float(x) for x in re.findall(
                num_form, command) if re.search(r'\d', x)]
            if len(numbers) > 0:
                raise IOError(
                    TextColors.FAIL + 'Cannot handle multi-line VMEC inputs!' + TextColors.ENDC)

    cP *= pres_scale
    desc_file.write('\n')
    desc_file.write('# pressure and rotational transform profiles\n')
    for k in range(max(cP.size, cI.size)):
        if k >= cP.size:
            desc_file.write(
                'l: {:3d}\tcP = {:16.8E}\tcI = {:16.8E}\n'.format(k, 0.0, cI[k]))
        elif k >= cI.size:
            desc_file.write(
                'l: {:3d}\tcP = {:16.8E}\tcI = {:16.8E}\n'.format(k, cP[k], 0.0))
        else:
            desc_file.write(
                'l: {:3d}\tcP = {:16.8E}\tcI = {:16.8E}\n'.format(k, cP[k], cI[k]))

    desc_file.write('\n')
    desc_file.write('# magnetic axis initial guess\n')
    for k in range(np.shape(axis)[0]):
        desc_file.write('n: {:3d}\taR = {:16.8E}\taZ = {:16.8E}\n'.format(
            int(axis[k, 0]), axis[k, 1], axis[k, 2]))

    desc_file.write('\n')
    desc_file.write('# fixed-boundary surface shape\n')
    for k in range(np.shape(bdry)[0]):
        desc_file.write('m: {:3d}\tn: {:3d}\tbR = {:16.8E}\tbZ = {:16.8E}\n'.format(
            int(bdry[k, 0]), int(bdry[k, 1]), bdry[k, 2], bdry[k, 3]))

    desc_file.truncate()

    # close files
    vmec_file.close()
    desc_file.close()